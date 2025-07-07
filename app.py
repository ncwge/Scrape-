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

        # Attempt JSON-LD extraction
        ld_json = None
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or tag.text)
            except Exception:
                continue
            # Handle list or dict
            entries = data if isinstance(data, list) else [data]
            for entry in entries:
                if isinstance(entry, dict) and entry.get("@type") == "Product":
                    ld_json = entry
                    break
            if ld_json:
                break

        # If JSON-LD not found, fallback to HTML scraping
        if ld_json:
            brand = ld_json.get("brand", {}).get("name") or ld_json.get("manufacturer", {}).get("name") or "n/a"
            model = ld_json.get("sku") or ld_json.get("mpn") or "n/a"
            description = ld_json.get("description") or "n/a"
        else:
            # Brand from image alt
            img = soup.select_one('.vendorLogo img, .brand-logo img')
            brand = img['alt'].strip() if img and img.has_attr('alt') else 'n/a'
            # Model from page text
            model_el = soup.select_one('.sku, .product-sku')
            if not model_el:
                dt = soup.find('dt', string=lambda t: t and 'Model' in t)
                model_el = dt.find_next_sibling('dd') if dt else None
            model = model_el.get_text(strip=True) if model_el else 'n/a'
            # Description block
            desc_el = soup.select_one('#productDescription, .prodDesc, .longdesc, .shortDescription')
            if desc_el:
                paras = desc_el.find_all('p')
                description = ' '.join(p.get_text(strip=True) for p in paras) if paras else desc_el.get_text(' ', strip=True)
            else:
                description = 'n/a'

        # Display results
        st.subheader("Results")
        st.write("**Brand:**", brand)
        st.write("**Model:**", model)
        st.write("**Description:**", description)
