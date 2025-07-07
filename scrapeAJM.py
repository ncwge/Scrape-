import re
import streamlit as st
import requests
import json
from bs4 import BeautifulSoup
import pandas as pd

st.set_page_config(page_title="AJMadison SKU Lookup", layout="centered")
st.title("AJMadison SKU Lookup")

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
        full = parent.get_text(separator=' ', strip=True)
        value = full[len(span.get_text()):].strip()
        key = label.lower().replace(' ', '_')
        if value:
            data[key] = value
        # 3) Extract List Price from schema.org Offer block
    offer_table = soup.select_one('table[itemtype="https://schema.org/Offer"]')
    if offer_table:
        for tr in offer_table.select('tr'):
            tds = tr.find_all('td')
            if len(tds) >= 2:
                label = tds[0].get_text(strip=True).rstrip(':').lower().replace(' ', '_')
                price_td = tds[1]
                # try <del> tag
                del_tag = price_td.find('del')
                if del_tag:
                    price = del_tag.get_text(strip=True)
                else:
                    meta_price = price_td.find('meta', attrs={'itemprop': 'price'})
                    price = meta_price['content'] if meta_price else price_td.get_text(strip=True)
                data[label] = price
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
        # Extract specs only
        specs = scrape_specs(soup)

        if specs:
            st.subheader("All Extracted Attributes")
            rows = [{"Attribute": k.replace('_', ' ').capitalize(), "Value": v}
                    for k, v in specs.items()]
            df = pd.DataFrame(rows)
            st.table(df)
        else:
            st.info("No attributes found.")
