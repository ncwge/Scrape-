import streamlit as st
import requests
from bs4 import BeautifulSoup
import json

st.set_page_config(page_title="AJMadison SKU Lookup", layout="centered")
st.title("AJMadison SKU Lookup")

sku = st.text_input("Enter SKU", placeholder="e.g. CJE23DP2WS1").strip().upper()

if st.button("Fetch") and sku:
    st.info(f"Looking up SKU: {sku}")
    details = {}
    source = None

    # 1. Try the JSON API
    try:
        json_url = f"https://www.ajmadison.com/cgi-bin/ajmadison/packages.index.json.php?sku={sku}"
        resp = requests.get(json_url, timeout=5)
        resp.raise_for_status()
        item = resp.json().get("item", {})
        if item:
            details['Brand'] = item.get('brand')
            details['Model'] = item.get('sku')
            details['Description'] = item.get('child_label') or item.get('quickspecs', {}).get('Short Description')
            source = 'JSON API'
    except Exception:
        source = None

    # 2. Fallback: Fetch via CGI HTML
    if not details or not all(details.values()):
        try:
            url = f"https://www.ajmadison.com/cgi-bin/ajmadison/{sku}.html"
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # JSON-LD extraction
            ld_json = None
            for tag in soup.find_all("script", type="application/ld+json"):
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
            if ld_json:
                details['Brand'] = ld_json.get('brand', {}).get('name')
                details['Model'] = ld_json.get('sku')
                details['Description'] = ld_json.get('description')
                source = 'JSON-LD'
            else:
                # Simple HTML selectors
                bimg = soup.select_one('.vendorLogo img, .brand-logo img')
                details['Brand'] = bimg['alt'].strip() if bimg and bimg.has_attr('alt') else None
                mdl = soup.select_one('.sku, .product-sku')
                details['Model'] = mdl.get_text(strip=True) if mdl else None
                desc = soup.select_one('#productDescription, .prodDesc, .longdesc, .shortDescription')
                if desc:
                    ps = desc.find_all('p')
                    details['Description'] = ' '.join(p.get_text(strip=True) for p in ps) if ps else desc.get_text(' ', strip=True)
                source = 'HTML scrape'
        except Exception:
            pass

    # Display
    st.subheader("Results")
    if details:
        for k, v in details.items():
            st.write(f"**{k}:** {v or 'n/a'}")
        st.caption(f"(Source: {source or 'multiple'})")
    else:
        st.error("Unable to retrieve data for that SKU.")
