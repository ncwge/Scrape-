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
    Rule-based parser to extract key features from a free-text description.
    """
    text = desc.lower()
    tokens = re.split(r',| and ', text)
    attrs = {}
    # Generic
    if m := re.search(r"(\d+(?:\.\d+)?)\s*cu\.?\s*ft", text): attrs['capacity'] = m.group(0)
    if m := re.search(r"(\d+)\s*inch", text): attrs['size'] = m.group(0)
    # Color
    for color in ('black','white','stainless steel','gray','silver','white-on-white'):
        if color in text: attrs['color'] = color; break
    # Appliance type
    for app in ('microwave','range hood','dishwasher','refrigerator','oven','cooktop','washer','dryer'):
        if app in text: attrs['appliance'] = app; break
    # Description features
    for t in tokens:
        t = t.strip()
        if 'cfm' in t: attrs.setdefault('blower', []).append(t)
        elif 'speed' in t: attrs.setdefault('speeds', []).append(t)
        elif 'lighting' in t: attrs.setdefault('lighting', []).append(t)
        elif 'filter' in t: attrs.setdefault('filters', []).append(t)
        elif re.search(r'\d+-minute', t): attrs.setdefault('install_time', []).append(t)
        elif 'convertible' in t: attrs['venting'] = 'convertible'
        elif 'cook' in t: attrs.setdefault('features', []).append(t)
        elif 'ul listed' in t or 'cul listed' in t: attrs.setdefault('certifications', []).append(t)
    return attrs

# --- Sidebar & Spec scraping utility ---
def scrape_specs(soup: BeautifulSoup) -> dict:
    """
    Extract specs from <dl> lists and any bold label spans (e.g., Height: spans).
    """
    data = {}
    # 1) Scrape all dt/dd pairs
    for dl in soup.find_all('dl'):
        for dt, dd in zip(dl.find_all('dt'), dl.find_all('dd')):
            key = dt.get_text(strip=True).rstrip(':').lower().replace(' ', '_')
            data[key] = dd.get_text(strip=True)
    # 2) Scrape any <span class="bold black">Label:</span>Value siblings
    for span in soup.select('span.bold.black'):
        label = span.get_text(strip=True).rstrip(':')
        parent = span.parent
        # get the rest of the text in the parent, after the span
        full = parent.get_text(separator=' ', strip=True)
        # remove the label from the full text
        value = full[len(span.get_text()):].strip()
        key = label.lower().replace(' ', '_')
        if value:
            data[key] = value
    return data

# --- UI ---
sku = st.text_input("Enter SKU (model number)", placeholder="e.g. CJE23DP2WS1").strip().upper()
if st.button("Fetch") and sku:
    st.info(f"Fetching data for SKU: {sku}")
    url = f"https://www.ajmadison.com/cgi-bin/ajmadison/{sku}.html"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Referer": "https://www.ajmadison.com/"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        st.error(f"Failed to load product page: {e}")
        return
    soup = BeautifulSoup(html, "html.parser")
    # JSON-LD fallback
    ld_json = None
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            d = json.loads(tag.string or tag.text)
        except:
            continue
        recs = d if isinstance(d, list) else [d]
        for rec in recs:
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
        brand, model, description = (parts + [sku, 'n/a'])[:3]
    st.subheader("Results")
    st.write(f"**Brand:** {brand}")
    st.write(f"**Model:** {model}")
    st.write(f"**Description:** {description}")
    # Combine parsed description and scraped specs
    parsed = parse_desc(description)
    specs = scrape_specs(soup)
    combined = {**specs, **parsed}
    if combined:
        st.subheader("All Extracted Attributes")
        rows = [{"Attribute": k.replace('_', ' ').capitalize(), "Value": v} for k, v in combined.items()]
        df = pd.DataFrame(rows)
        st.table(df)
    else:
        st.info("No attributes found.")
