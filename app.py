import os
import json
import requests
import streamlit as st
import trafilatura
from dotenv import load_dotenv
import openai

# Load API keys
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# Load clinical dataset
with open("clinical_interests.json", "r", encoding="utf-8") as f:
    full_dataset = json.load(f)

specialty_list = sorted(set(item["specialty"] for item in full_dataset))

# Streamlit UI
st.set_page_config(page_title="Target Killer: Clinical Mapper", layout="centered")
st.title("🎯 Target Killer: Clinical Interest Edition")
st.markdown("##### Your Monthly Target Savior")

specialty = st.selectbox("Select Specialty", specialty_list)
name = st.text_input("Expert Name", placeholder="e.g. Dr. Peter Weil")

def get_filtered_data(specialty):
    entry = next((i for i in full_dataset if i["specialty"] == specialty), None)
    return {
        sub["name"]: sub["clinical_interests"]
        for sub in entry["sub_specialties"]
    }

# Search in 2 tiers (clinical platforms → fallback)
def get_clinical_snippets(name):
    tier1 = f"{name} conditions treated OR clinical expertise OR subspecialties site:healthgrades.com OR site:usnews.com OR site:sharecare.com"
    snippets = serpapi_snippets(tier1)
    if snippets:
        return " | ".join(snippets)

    tier2 = f"{name} clinical interest OR areas of expertise site:hospital OR site:.edu OR site:.org"
    return " | ".join(serpapi_snippets(tier2))

def serpapi_snippets(query):
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": 5
    }
    try:
        res = requests.get("https://serpapi.com/search", params=params)
        results = res.json().get("organic_results", [])
        return [r.get("snippet", "") for r in results if r.get("snippet")]
    except:
        return []

# Updated prompt with strict sub-specialty mapping logic
def build_prompt(snippets, dataset, specialty):
    return f"""
You are a clinical interest mapping assistant.

Text:
{snippets}

Dataset for specialty: {specialty}
{json.dumps(dataset, indent=2)}

Instructions:
- Carefully examine the provided text.
- For **every sub-specialty** in the dataset, check if **any** of its clinical interests are:
  - directly mentioned,
  - partially referenced,
  - or strongly implied by context.
- Include all sub-specialties that apply.
- ONLY use sub-specialties and interests from the dataset.
- NEVER make up or assume terms not in the dataset.

Output format:
Sub-specialty: [Sub-specialty name]
→ Clinical Interest: [Interest 1]
→ Clinical Interest: [Interest 2]
"""

# On button press
if st.button("Map Clinical Interests") and name and specialty:
    st.info("🔍 Searching expert's clinical expertise...")
    clinical_text = get_clinical_snippets(name)

    if not clinical_text or len(clinical_text) < 40:
        st.error("❌ No relevant clinical content found.")
    else:
        st.success("✅ Clinical content found. Sending to GPT...")

        st.markdown("### 🔍 Extracted Clinical Snippets")
        st.write(clinical_text)

        dataset = get_filtered_data(specialty)
        prompt = build_prompt(clinical_text, dataset, specialty)

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        result = response.choices[0].message.content.strip()
        st.markdown("### ✅ Mapped Clinical Interests")
        st.code(result, language="markdown")

# Footer
st.markdown("---")
st.markdown("**Made by HOBZ — Inspired by BEDO**")
