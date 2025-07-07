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
    install_time, venting, certifications, finish, color, and appliance type.
    """
    text = desc.lower()
    tokens = re.split(r',| and ', text)
    attrs = {}

    # Generic attributes
    if m := re.search(r"(\d+(?:\.\d+)?)\s*cu\.?\s*ft", text):
        attrs['capacity'] = m.group(0)
    if m := re.search(r"(\d+)\s*inch", text):
        attrs['size'] = m.group(0)

    # Detect color/finish first
    colors = ['black', 'white', 'stainless steel', 'gray', 'silver', 'white-on-white']
    for color in colors:
        if color in text:
            attrs['color'] = color
            break

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
        elif 'ul listed' in t or 'cul listed' in t:
            attrs.setdefault('certifications', []).append(t)
        elif 'stainless steel' in t and 'color' not in attrs:
            attrs['finish'] = 'stainless steel'
    return attrs

# --- Sidebar scraping utility ---
def scrape_sidebar(soup: BeautifulSoup, sections: list) -> dict:
    """
    Extract dt/dd pairs under given section headings.
    Returns a flat dict of {key: value}.
    """
    data = {}
    for section in sections:
        header = soup.find(lambda tag: tag.name in ['h2', 'h3', 'h4'] and section.lower() in tag.get_text(strip=True).lower())
        if not header:
            continue
        dl = header.find_next_sibling('dl')
        if not dl:
            continue
        for dt, dd in zip(dl.find_all('dt'), dl.find_all('dd')):
            key = f"{section}_{dt.get_text(strip=True).rstrip(':')}".lower().replace(' ', '_')
            value = dd.get_text(strip=True)
            data[key] = value
    return data

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

        # JSON-LD fallback
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

        # Parsed description attributes
        parsed = parse_desc(description)
        # Scrape sidebar sections
        sections = ["Product Information", "Appearance", "Dimensions", "Smart", "Capacity", "Features", "Technical Details"]
        sidebar_data = scrape_sidebar(soup, sections)

        # Combine and show
        combined = {**sidebar_data, **parsed}
        if combined:
            st.subheader("All Extracted Attributes")
            rows = []
            for key, val in combined.items():
                rows.append({"Attribute": key.replace('_', ' ').capitalize(), "Value": val})
            df = pd.DataFrame(rows)
            st.table(df)
        else:
            st.info("No attributes found.")
