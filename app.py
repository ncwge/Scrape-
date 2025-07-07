import streamlit as st
import requests
import json

st.set_page_config(page_title="AJMadison SKU Lookup (JSON Only)", layout="centered")
st.title("AJMadison SKU Lookup (JSON Only)")

sku = st.text_input("Enter model number (SKU)", placeholder="e.g. CJE23DP2WS1").strip().upper()

if st.button("Fetch") and sku:
    st.info(f"Fetching data from JSON API for SKU: {sku}")
    try:
        api_url = f"https://www.ajmadison.com/cgi-bin/ajmadison/packages.index.json.php?sku={sku}"
        resp = requests.get(api_url, headers={"Accept": "application/json"}, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("item")
        if not data:
            st.error("No JSON data returned for this SKU.")
        else:
            # Display JSON fields
            st.subheader("Results")
            st.write(f"**Brand:** {data.get('brand', 'n/a')}")
            st.write(f"**Model:** {data.get('sku', 'n/a')}")
            desc = data.get('child_label') or data.get('quickspecs', {}).get('Short Description', 'n/a')
            st.write(f"**Description:** {desc}")
    except Exception as e:
        st.error(f"Error retrieving JSON API: {e}")
