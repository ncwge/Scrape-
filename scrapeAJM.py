import re
import streamlit as st
import requests
import json
from bs4 import BeautifulSoup
import pandas as pd
from io import BytesIO

# --- Page Setup ---
st.set_page_config(page_title="AJMadison SKU Lookup & Batch Extractor", layout="centered")
st.title("AJMadison SKU Lookup & Batch Extractor")

# --- SKU Input Utilities ---
@st.cache_data
def extract_skus_from_excel(df: pd.DataFrame) -> list:
    pattern = re.compile(r"\b[A-Z]{2,}[0-9]{2,}[A-Z0-9]*\b")
    skus, seen = [], set()
    for text in df.astype(str).values.flatten():
        for m in pattern.findall(text):
            if len(m) >= 6 and m not in seen:
                skus.append(m)
                seen.add(m)
    return skus

@st.cache_data
def extract_skus_from_text(text: str) -> list:
    pattern = re.compile(r"\b[A-Z]{2,}[0-9]{2,}[A-Z0-9]*\b")
    skus, seen = [], set()
    for line in text.upper().splitlines():
        for m in pattern.findall(line):
            if len(m) >= 6 and m not in seen:
                skus.append(m)
                seen.add(m)
    return skus

# --- Spec Scraper ---
def scrape_specs(soup: BeautifulSoup) -> dict:
    data = {}
    # scrape all dl dt/dd pairs
    for dl in soup.find_all('dl'):
        for dt, dd in zip(dl.find_all('dt'), dl.find_all('dd')):
            key = dt.get_text(strip=True).rstrip(':').lower().replace(' ', '_')
            data[key] = dd.get_text(strip=True)
    # scrape bold black spans
    for span in soup.select('span.bold.black'):
        label = span.get_text(strip=True).rstrip(':')
        parent = span.parent
        full = parent.get_text(separator=' ', strip=True)
        value = full[len(span.get_text()):].strip()
        if value:
            data[label.lower().replace(' ', '_')] = value
    # list price
    offer = soup.select_one('table[itemtype="https://schema.org/Offer"]')
    if offer:
        for tr in offer.select('tr'):
            tds = tr.find_all('td')
            if len(tds) < 2: continue
            label = tds[0].get_text(strip=True).rstrip(':').lower()
            if label == 'list price':
                price_td = tds[1]
                del_tag = price_td.find('del')
                price = del_tag.get_text(strip=True) if del_tag else (
                    price_td.find('meta', {'itemprop':'price'})['content']
                    if price_td.find('meta', {'itemprop':'price'}) else price_td.get_text(strip=True)
                )
                data['list_price'] = price
                break
    return data

# --- UI: Batch Extractor ---
st.header("Batch Competitor SKU Extractor")
col1, col2 = st.columns(2)
with col1:
    uploaded = st.file_uploader("Upload Excel file of SKUs", type=["xls","xlsx"] )
with col2:
    pasted = st.text_area("Or paste SKUs here (one per line)")

skus = []
if uploaded:
    # Read uploaded file into BytesIO to ensure compatibility
    file_bytes = uploaded.read()
    try:
        df_in = pd.read_excel(BytesIO(file_bytes), header=None, engine='openpyxl')
    except Exception:
        df_in = pd.read_excel(BytesIO(file_bytes), header=None)
    skus = extract_skus_from_excel(df_in)
elif pasted:
    skus = extract_skus_from_text(pasted)
else:
    skus = []
    skus = []
    skus = extract_skus_from_text(pasted)

if skus:
    st.success(f"Found {len(skus)} SKUs.")
    for sku in skus:
        with st.expander(f"Details for {sku}"):
            try:
                resp = requests.get(f"https://www.ajmadison.com/cgi-bin/ajmadison/{sku}.html",
                                     headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, 'html.parser')
                specs = scrape_specs(soup)
                if specs:
                    df_specs = pd.DataFrame([{"Attribute":k.replace('_',' ').capitalize(), "Value":v}
                                              for k,v in specs.items()])
                    st.table(df_specs)
                else:
                    st.warning("No specs found.")
            except Exception as e:
                st.error(f"Failed to fetch {sku}: {e}")
else:
    st.info("Upload or paste SKUs to begin batch extraction.")

# --- UI: Single SKU Lookup ---
st.markdown("---")
st.header("Single AJMadison SKU Lookup")
single_sku = st.text_input("Enter single SKU (e.g. JVX3300SJSS)").strip().upper()
if st.button("Fetch Single SKU") and single_sku:
    st.info(f"Fetching details for {single_sku}...")
    try:
        resp = requests.get(f"https://www.ajmadison.com/cgi-bin/ajmadison/{single_sku}.html",
                             headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        specs = scrape_specs(soup)
        if specs:
            df_single = pd.DataFrame([{"Attribute":k.replace('_',' ').capitalize(), "Value":v}
                                       for k,v in specs.items()])
            st.table(df_single)
        else:
            st.warning("No specs found.")
    except Exception as e:
        st.error(f"Failed to fetch {single_sku}: {e}")
