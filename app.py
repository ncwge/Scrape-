import streamlit as st
import requests
from bs4 import BeautifulSoup
import json

st.set_page_config(page_title="AJMadison SKU Lookup", layout="centered")
st.title("AJMadison SKU Lookup")

sku = st.text_input("Enter SKU", placeholder="e.g. CJE23DP2WS1").strip().upper()

if st.button("Fetch") and sku:
    url = f"https://www.ajmadison.com/cgi-bin/ajmadison/{sku}.html"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except Exception as e:
        st.error(f"Could not fetch product page: {e}")
    else:
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find JSON-LD Product metadata
        ld_json = None
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string)
                if isinstance(data, dict) and data.get("@type") == "Product":
                    ld_json = data
                    break
            except Exception:
                continue

        if not ld_json:
            st.error("Product metadata not found on page.")
        else:
            brand       = ld_json.get("brand", {}).get("name") or ld_json.get("manufacturer", {}).get("name", "n/a")
            model       = ld_json.get("sku", "n/a")
            description = ld_json.get("description", "n/a")

            st.subheader("Results")
            st.write("**Brand:**", brand)
            st.write("**Model:**", model)
            st.write("**Description:**", description)
