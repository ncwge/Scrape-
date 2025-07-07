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

        # Find JSON-LD that describes the product
        ld_json = None
        for tag in soup.find_all("script", type="application/ld+json"):
            text = tag.string or tag.text
            try:
                data = json.loads(text)
            except Exception:
                continue
            # JSON-LD might be a list or a dict
            candidates = data if isinstance(data, list) else [data]
            for entry in candidates:
                if isinstance(entry, dict) and entry.get("@type") == "Product":
                    ld_json = entry
                    break
            if ld_json:
                break

        if not ld_json:
            st.error("Product metadata not found on page.")
        else:
            # Extract fields from JSON-LD
            brand = (ld_json.get("brand", {}).get("name")
                     or ld_json.get("manufacturer", {}).get("name")
                     or "n/a")
            model = ld_json.get("sku") or ld_json.get("mpn") or "n/a"
            description = ld_json.get("description") or "n/a"

            st.subheader("Results")
            st.write("**Brand:**", brand)
            st.write("**Model:**", model)
            st.write("**Description:**", description)
