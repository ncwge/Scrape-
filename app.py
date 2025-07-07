import streamlit as st
import requests
import json
from bs4 import BeautifulSoup

st.set_page_config(page_title="AJMadison SKU Lookup", layout="centered")
st.title("AJMadison SKU Lookup")

# User inputs the model number (SKU)
sku = st.text_input("Enter SKU (model number)", placeholder="e.g. CJE23DP2WS1").strip().upper()

if st.button("Fetch") and sku:
    st.info(f"Fetching data for SKU: {sku}")

    # Build the CGI-bin product URL dynamically
    url = f"https://www.ajmadison.com/cgi-bin/ajmadison/{sku}.html"
    try:
        # Fetch the public HTML page
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                   "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                   "Referer": "https://www.ajmadison.com/"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        st.error(f"Failed to load product page: {e}")
    else:
        # Parse the HTML and extract the JSON-LD Product block
        soup = BeautifulSoup(html, "html.parser")
        ld_json = None
        for tag in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(tag.string or tag.text)
            except Exception:
                continue
            entries = data if isinstance(data, list) else [data]
            for entry in entries:
                if entry.get("@type") == "Product":
                    ld_json = entry
                    break
            if ld_json:
                break

        if not ld_json:
            st.error("Product metadata not found on page.")
        else:
            # Extract brand, model, description from JSON-LD
            brand = ld_json.get('brand', {}).get('name', 'n/a')
            model = ld_json.get('sku', sku)
            description = ld_json.get('description', 'n/a')

            # Display the results
            st.subheader("Results")
            st.write(f"**Brand:** {brand}")
            st.write(f"**Model:** {model}")
            st.write(f"**Description:** {description}")

