import re
import streamlit as st
import requests
import json
from bs4 import BeautifulSoup
import pandas as pd

st.set_page_config(page_title="AJMadison SKU Lookup", layout="centered")
st.title("AJMadison SKU Lookup")

# --- Parsing utility ---
def parse_desc(desc: str) -> dict:
    """
    Rule-based parser to extract attributes from any appliance description.
    Returns a dict of features like size, capacity, mount, blower, speeds, lighting, filters,
    install_time, venting, certifications, finish, and appliance type.
    """
    text = desc.lower()
    tokens = re.split(r',| and ', text)
    attrs = {}

    # Generic attributes
    if m := re.search(r"(\d+(?:\.\d+)?)\s*cu\.?\s*ft", text):
        attrs['capacity'] = m.group(0)
    if m := re.search(r"(\d+)\s*inch", text):
        attrs['size'] = m.group(0)
    # Appliance type
    for appliance in ('microwave', 'range hood', 'dishwasher', 'refrigerator', 'oven', 'cooktop', 'washer', 'dryer'):
        if appliance in text:
            attrs['appliance'] = appliance
            break

    # Feature-specific rules
    for t in tokens:
        t = t.strip()
        if 'under cabinet' in t:
            attrs['mount'] = 'under cabinet'
        elif 'over-the-range' in t or 'over the range' in t:
            attrs['mount'] = 'over the range'
        elif 'cfm' in t:
            attrs.setdefault('blower', []).append(t)
        elif 'speed' in t:
            attrs.setdefault('speeds', []).append(t)
        elif 'incandes' in t:
            attrs.setdefault('lighting', []).append('incandescent')
        elif 'led lighting' in t or 'led light' in t:
            attrs.setdefault('lighting', []).append('led')
        elif 'dishwasher safe' in t:
            attrs.setdefault('filters', []).append('dishwasher safe')
        elif re.search(r'\d+-minute', t):
            attrs.setdefault('install_time', []).append(t)
        elif 'convertible vent' in t or 'convertible' in t:
            attrs['venting'] = 'convertible'
        elif 'quick start' in t:
            attrs.setdefault('features', []).append('quick start')
        elif 'auto cook' in t:
            attrs.setdefault('features', []).append('auto cook')
        elif any(cert in t for cert in ('ul listed', 'cul listed', 'list')):
            attrs.setdefault('certifications', []).append(t)
        elif 'stainless steel' in t:
            attrs['finish'] = 'stainless steel'
        # add more generic rules as needed
    return attrs

# --- UI ---
sku = st.text_input("Enter SKU (model number)", placeholder="e.g. CJE23DP2WS1").strip().upper()

if st.button("Fetch") and sku:
    st.info(f"Fetching data for SKU: {sku}")

    url = f"https://www.ajmadison.com/cgi-bin/ajmadison/{sku}.html"
    headers = {
        "User-Agent": "Mozilla/5.0",
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
        # Find JSON-LD Product
        ld_json = None
        for tag in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(tag.string or tag.text)
            except Exception:
                continue
            for rec in (data if isinstance(data, list) else [data]):
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
            title = soup.title.string if soup.title else ''
            main = title.split('|')[0].strip()
            parts = main.split(' ', 2)
            brand = parts[0] if parts else 'n/a'
            model = parts[1] if len(parts) > 1 else sku
            description = parts[2] if len(parts) > 2 else 'n/a'

        # Display results
        st.subheader("Results")
        st.write(f"**Brand:** {brand}")
        st.write(f"**Model:** {model}")
        st.write(f"**Description:** {description}")

        # Parse description
        parsed = parse_desc(description)
        if parsed:
            st.subheader("Parsed Attributes")
            # Convert to table
            rows = []
            for key, val in parsed.items():
                if isinstance(val, list):
                    val_str = ", ".join(val)
                else:
                    val_str = val
                rows.append({"Attribute": key.capitalize(), "Value": val_str})
            df = pd.DataFrame(rows)
            st.table(df)
        else:
            st.info("No attributes parsed.")
