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
    Extract specs from <dl> lists, bold span labels, and the List Price.
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

    # 3) Extract List Price from <td class="right-align table-cell-minified">
    price_td = soup.find("td", class_="right-align table-cell-minified")
    if price_td:
        price_text = price_td.get_text(strip=True)
        if price_text.startswith('$'):
            data["list_price"] = price_text

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

            # ✅ Ensure list_price is at the top of the table
            rows = []
            if "list_price" in specs:
                rows.append({
                    "Attribute": "List price",
                    "Value": specs.pop("list_price")
                })
            for k, v in specs.items():
                rows.append({
                    "Attribute": k.replace('_', ' ').capitalize(),
                    "Value": v
                })

            df = pd.DataFrame(rows)
            st.table(df)
        else:
            st.info("No attributes found.")
