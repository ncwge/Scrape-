import streamlit as st
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="AJMadison SKU Lookup", layout="centered")
st.title("AJMadison SKU Lookup")

sku = st.text_input("Enter SKU (model number)", placeholder="e.g. CJE23DP2WS1").strip().upper()

if st.button("Fetch") and sku:
    st.info(f"Fetching data for SKU: {sku}")
    # Construct the product page URL dynamically
    url = f"https://www.ajmadison.com/cgi-bin/ajmadison/{sku}.html"
    try:
        # Fetch the raw HTML page
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        st.error(f"Failed to load product page: {e}")
    else:
        soup = BeautifulSoup(html, "html.parser")
        # Extract Brand & Model from page <title>
        title = soup.title.string if soup.title else ''
        # Title typically: "Brand Model Description | AJMadison"
        parts = title.split('|')[0].split(' ', 2)
        brand = parts[0] if len(parts) > 0 else 'n/a'
        model = parts[1] if len(parts) > 1 else sku
        description = parts[2] if len(parts) > 2 else 'n/a'

                # Display results
        st.subheader("Results")
        st.write(f"**Brand:** {brand}")
        st.write(f"**Model:** {model}")
        st.write(f"**Description:** {description}")

        # Now parse the Product Information table for additional specs
        specs = {}
        # look for table by caption or id
        table = soup.find('table', id='productInformation') or soup.find('table', class_='ProductInformation')
        if table:
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) == 2:
                    label = cols[0].get_text(strip=True).rstrip(':')
                    value = cols[1].get_text(strip=True)
                    specs[label] = value
        else:
            # fallback: dt/dd pairs under a div
            for dt in soup.select('dt'):
                dd = dt.find_next_sibling('dd')
                if dd:
                    label = dt.get_text(strip=True).rstrip(':')
                    value = dd.get_text(strip=True)
                    specs[label] = value

        if specs:
            st.subheader("Additional Specs")
            for label, value in specs.items():
                st.write(f"**{label}:** {value}")
        else:
            st.info("No additional product specs found on the page.")
