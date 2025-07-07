import streamlit as st
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="AJMadison SKU Lookup", layout="centered")
st.title("AJMadison SKU Lookup")

sku = st.text_input("Enter SKU (model number)", placeholder="e.g. CJE23DP2WS1").strip().upper()

if st.button("Fetch") and sku:
    st.info(f"Fetching data for SKU: {sku}")
    # Use the public product page URL to avoid 403
    url = f"https://www.ajmadison.com/{sku}.html"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        st.error(f"Failed to load product page: {e}")
    else:
        soup = BeautifulSoup(html, "html.parser")
        # Extract brand, model, description from <title>
        # Format is "Brand Model Description | AJMadison"
        title_text = (soup.title.string or '').split('|')[0].strip()
        parts = title_text.split(' ', 2)
        brand = parts[0] if len(parts) > 0 else 'n/a'
        model = parts[1] if len(parts) > 1 else sku
        description = parts[2] if len(parts) > 2 else 'n/a'

        # Display results
        st.subheader("Results")
        st.write(f"**Brand:** {brand}")
        st.write(f"**Model:** {model}")
        st.write(f"**Description:** {description}")
