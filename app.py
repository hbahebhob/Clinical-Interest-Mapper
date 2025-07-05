import os
import json
import streamlit as st
import requests
import trafilatura
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load .env values
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# Load clinical interests dataset
with open("clinical_interests.json", "r", encoding="utf-8") as f:
    dataset = json.load(f)

specialties = sorted(list(set(item["specialty"] for item in dataset if "specialty" in item)))

# -------------------------------
# 🧠 Improved snippet extraction logic with fallback
# -------------------------------
def extract_snippets(query: str, lang="en") -> str:
    try:
        st.write(f"🔍 Searching Google for: `{query}`")

        response = requests.get("https://serpapi.com/search", params={
            "q": query,
            "engine": "google",
            "api_key": SERPAPI_KEY,
            "hl": lang,
            "num": 5
        })

        data = response.json()
        links = [res["link"] for res in data.get("organic_results", []) if "link" in res]

        snippets = ""
        for url in links:
            downloaded = trafilatura.fetch_url(url)

            # Fallback to requests + BeautifulSoup if trafilatura fails
            if not downloaded:
                try:
                    page = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
                    soup = BeautifulSoup(page.content, "html.parser")
                    text = soup.get_text(separator="\n")
                except Exception:
                    continue
            else:
                text = trafilatura.extract(downloaded)

            if text and len(text.strip()) > 100:
                snippets += text.strip() + "\n---\n"

        return snippets.strip()

    except Exception as e:
        st.warning(f"Error during search: {e}")
        return ""

# -------------------------------
# 🔎 GPT-based interest mapping
# -------------------------------
import openai
openai.api_key = OPENAI_API_KEY

def map_clinical_interests(text: str, name: str, specialty: str) -> str:
    with open("clinical_interests.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)

    system_prompt = (
        f"You are a clinical data analyst. You will receive a text about Dr. {name}'s clinical interests. "
        f"Map their specialties and clinical interests strictly using the provided dataset. "
        f"Only output matching specialties and interests from the JSON file. "
        f"If the terms don't exactly match, try your best to match them semantically to the closest valid entry. "
        f"Do not include any clinical interest that isn't listed in the dataset."
    )

    user_prompt = (
        f"Expert name: Dr. {name}\n"
        f"Specialty: {specialty}\n\n"
        f"Text:\n{text}\n\n"
        f"Dataset:\n{json.dumps(json_data)}"
    )

    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3
    )

    return completion.choices[0].message.content.strip()

# -------------------------------
# 🎯 Streamlit UI
# -------------------------------
st.set_page_config(page_title="Clinical Interest Mapper", page_icon="🎯")
st.title("🎯 Target Killer: Clinical Interest Edition")
st.markdown("### Your Monthly Target Savior")

with st.form("input_form"):
    col1, col2 = st.columns(2)
    specialty = col1.selectbox("Select Specialty", specialties)
    expert_name = col2.text_input("Expert Name", placeholder="e.g. Peter Weil")

    submit = st.form_submit_button("Map Clinical Interests")

if submit:
    with st.spinner("🔍 Searching expert's clinical expertise..."):
        queries = [
            f"{expert_name} {specialty} clinical interests",
            f"{expert_name} {specialty} areas of expertise",
            f"{expert_name} {specialty} diseases treated",
            f"{expert_name} {specialty} procedures",
        ]
        all_snippets = ""
        for q in queries:
            all_snippets += extract_snippets(q) + "\n"

        if not all_snippets.strip():
            st.error("❌ No relevant clinical content found.")
        else:
            st.success("✅ Clinical content found. Sending to GPT...")
            st.markdown("### 🔍 Extracted Clinical Snippets")
            st.code(all_snippets.strip())

            with st.spinner("🤖 Mapping to clinical interests..."):
                result = map_clinical_interests(all_snippets, expert_name, specialty)
                st.markdown("### ✅ Mapped Clinical Interests")
                st.code(result)
