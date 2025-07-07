import streamlit as st
import requests
import json

st.set_page_config(page_title="AJMadison SKU Lookup (JSON API)", layout="centered")
st.title("AJMadison SKU Lookup (JSON API)")

sku = st.text_input("Enter model number (SKU)", placeholder="e.g. CJE23DP2WS1").strip().upper()

if st.button("Fetch") and sku:
    st.info(f"Fetching JSON data for SKU: {sku}")
    try:
        api_url = f"https://www.ajmadison.com/cgi-bin/ajmadison/index.json.php?sku={sku}"
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": f"https://www.ajmadison.com/cgi-bin/ajmadison/{sku}.html",
            "User-Agent": "Mozilla/5.0"
        }
        resp = requests.get(api_url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        item = data.get('item') or data.get('Items') or None
        if not item:
            st.error("No JSON data found for this SKU.")
        else:
            st.subheader("Results")
            st.write("**Brand:**", item.get('brand', 'n/a'))
            st.write("**Model:**", item.get('sku', 'n/a'))
            desc = item.get('child_label') or item.get('quickspecs', {}).get('Short Description', 'n/a')
            st.write("**Description:**", desc)
    except Exception as e:
        st.error(f"Error fetching JSON API: {e}")
