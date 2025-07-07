import re
import streamlit as st
import requests
import json
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Competitor SKU Extractor", layout="centered")
st.title("Competitor SKU Extractor")

# --- SKU Input Utility ---
@st.cache_data
def extract_skus_from_excel(df: pd.DataFrame) -> list:
    all_text = df.astype(str).values.flatten()
    sku_pattern = re.compile(r"\b[A-Z]{2,}[0-9]{2,}[A-Z0-9]*\b")
    skus, seen = [], set()
    for text in all_text:
        for match in sku_pattern.findall(text):
            if len(match) >= 6 and match not in seen:
                skus.append(match)
                seen.add(match)
    return skus

@st.cache_data
def extract_skus_from_text(text: str) -> list:
    sku_pattern = re.compile(r"\b[A-Z]{2,}[0-9]{2,}[A-Z0-9]*\b")
    skus, seen = [], set()
    for line in text.upper().splitlines():
        for sku in sku_pattern.findall(line):
            if len(sku) >= 6 and sku not in seen:
                skus.append(sku)
                seen.add(sku)
    return skus

# --- Sidebar & Spec scraping utility ---
def scrape_specs(soup: BeautifulSoup) -> dict:
    data = {}
    for dl in soup.find_all('dl'):
        for dt, dd in zip(dl.find_all('dt'), dl.find_all('dd')):
            key = dt.get_text(strip=True).rstrip(':').lower().replace(' ', '_')
            data[key] = dd.get_text(strip=True)
    for span in soup.select('span.bold.black'):
        label = span.get_text(strip=True).rstrip(':')
        parent = span.parent
        full = parent.get_text(separator=' ', strip=True)
        value = full[len(span.get_text()):].strip()
        key = label.lower().replace(' ', '_')
        if value:
            data[key] = value
    offer_table = soup.select_one('table[itemtype="https://schema.org/Offer"]')
    if offer_table:
        for tr in offer_table.select('tr'):
            tds = tr.find_all('td')
            if len(tds) < 2:
                continue
            label_text = tds[0].get_text(strip=True).rstrip(':').lower()
            if label_text == 'list price':
                price_td = tds[1]
                del_tag = price_td.find('del')
                if del_tag:
                    price = del_tag.get_text(strip=True)
                else:
                    meta = price_td.find('meta', {'itemprop':'price'})
                    price = meta['content'] if meta else price_td.get_text(strip=True)
                data['list_price'] = price
                break
    return data

# --- UI: SKU ingestion ---
st.header("Step 1: Enter Competitor SKUs")
uploaded_file = st.file_uploader("Upload Excel file with SKUs", type=["xlsx","xls"] )
pasted_data = st.text_area("Or paste SKU data here:")
skus = []
if uploaded_file:
    df_upload = pd.read_excel(uploaded_file, header=None)
    skus = extract_skus_from_excel(df_upload)
elif pasted_data.strip():
    skus = extract_skus_from_text(pasted_data)

if not skus:
    st.info("Please upload a file or paste SKU data to proceed.")
else:
    st.success(f"✅ Found {len(skus)} unique SKUs.")
    # Display list and allow expanding details per SKU
    for sku in skus:
        with st.expander(f"Details for {sku}"):
            st.write(f"Fetching data for {sku}...")
            url = f"https://www.ajmadison.com/cgi-bin/ajmadison/{sku}.html"
            try:
                resp = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, 'html.parser')
                specs = scrape_specs(soup)
                if specs:
                    rows = [{"Attribute": k.replace('_',' ').capitalize(), "Value": v} for k,v in specs.items()]
                    df = pd.DataFrame(rows)
                    st.table(df)
                else:
                    st.warning("No attributes found for this SKU.")
            except Exception as e:
                st.error(f"Failed to fetch {sku}: {e}")
