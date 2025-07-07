import streamlit as st
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="AJMadison SKU Lookup", layout="centered")
st.title("AJMadison SKU Lookup")

sku = st.text_input("Enter SKU", placeholder="e.g. CJE23DP2WS1").strip().upper()

if st.button("Fetch") and sku:
    url = f"https://www.ajmadison.com/cgi-bin/ajmadison/{sku}.html"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except requests.HTTPError as e:
        st.error(f"Error fetching page: {e}")
    else:
        soup = BeautifulSoup(resp.text, "html.parser")

        # Brand from vendorLogo or brand-logo img alt
        brand_img = soup.select_one(".vendorLogo img, .brand-logo img")
        brand = brand_img["alt"].strip() if brand_img and brand_img.has_attr("alt") else "n/a"

        # Model from .sku (or fallback to dt:Model + dd)
        model_el = soup.select_one(".sku, .product-sku")
        if not model_el:
            dt = soup.find("dt", string=lambda t: t and "Model" in t)
            model_el = dt.find_next_sibling("dd") if dt else None
        model = model_el.get_text(strip=True) if model_el else "n/a"

        # Description from prodDesc / longdesc / shortDescription
        desc_el = (
            soup.select_one("#productDescription") or
            soup.select_one(".prodDesc") or
            soup.select_one(".longdesc") or
            soup.select_one(".shortDescription")
        )
        if desc_el:
            paras = desc_el.find_all("p")
            if paras:
                description = " ".join(p.get_text(strip=True) for p in paras)
            else:
                description = desc_el.get_text(" ", strip=True)
        else:
            description = "n/a"

        st.subheader("Results")
        st.write("**Brand:**", brand)
        st.write("**Model:**", model)
        st.write("**Description:**", description)
