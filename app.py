import streamlit as st
import requests
import json
from bs4 import BeautifulSoup

st.set_page_config(page_title="AJMadison SKU Lookup", layout="centered")
st.title("AJMadison SKU Lookup")

# Let user input model number (SKU)
sku = st.text_input("Enter SKU (model number)", placeholder="e.g. CJE23DP2WS1").strip().upper()

if st.button("Fetch") and sku:
    st.info(f"Fetching data for SKU: {sku}")

    # Correct CGI-bin HTML page URL
    url = f"https://www.ajmadison.com/cgi-bin/ajmadison/{sku}.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.ajmadison.com/"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        st.error(f"Failed to load product page: {e}")
    else:
        soup = BeautifulSoup(html, "html.parser")
                # Attempt embedded JSON-LD for Product
        ld_json = None
        for tag in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(tag.string or tag.text)
            except Exception:
                continue
            records = data if isinstance(data, list) else [data]
            for rec in records:
                if rec.get("@type") == "Product":
                    ld_json = rec
                    break
            if ld_json:
                break

        if ld_json:
            brand = ld_json.get('brand', {}).get('name', 'n/a')
            model = ld_json.get('sku', sku)
            description = ld_json.get('description', 'n/a')
        else:
            # Fallback: parse page <title> (format: "Brand Model Description | AJMadison")
            title = soup.title.string if soup.title else ''
            main = title.split('|')[0].strip()
            parts = main.split(' ', 2)
            brand = parts[0] if len(parts) > 0 else 'n/a'
            model = parts[1] if len(parts) > 1 else sku
            description = parts[2] if len(parts) > 2 else 'n/a'

        # Display results
        st.subheader("Results")
        st.write(f"**Brand:** {brand}")
        st.write(f"**Model:** {model}")
        st.write(f"**Description:** {description}")
