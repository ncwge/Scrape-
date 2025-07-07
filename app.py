import streamlit as st
import requests
from bs4 import BeautifulSoup
import json

st.set_page_config(page_title="AJMadison SKU Lookup", layout="centered")
st.title("AJMadison SKU Lookup")

sku = st.text_input("Enter SKU", placeholder="e.g. CJE23DP2WS1").strip().upper()

if st.button("Fetch") and sku:
    st.info(f"Looking up SKU: {sku}")
    details = {}
    source = None

    # 1. Try the JSON API
    try:
        json_url = f"https://www.ajmadison.com/cgi-bin/ajmadison/packages.index.json.php?sku={sku}"
        resp = requests.get(json_url, timeout=5)
        resp.raise_for_status()
        item = resp.json().get("item", {})
        if item:
            details['Brand'] = item.get('brand')
            details['Model'] = item.get('sku')
            details['Description'] = item.get('child_label') or item.get('quickspecs', {}).get('Short Description')
            source = 'JSON API'
    except Exception:
        source = None

    # 2. Fallback: Fetch via CGI HTML
    if not details or not all(details.values()):
        try:
            url = f"https://www.ajmadison.com/cgi-bin/ajmadison/{sku}.html"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.ajmadison.com/"
            }
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # JSON-LD extraction
            ld_json = None
            for tag in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(tag.string or tag.text)
                except Exception:
                    continue
                entries = data if isinstance(data, list) else [data]
                for entry in entries:
                    if entry.get("@type") == "Product":
                        ld_json = entry
                        break
                if ld_json:
                    break
            if ld_json:
                details['Brand'] = ld_json.get('brand', {}).get('name')
                details['Model'] = ld_json.get('sku')
                details['Description'] = ld_json.get('description')
                source = 'JSON-LD'
            else:
                # HTML scraping fallback
                bimg = soup.select_one('.vendorLogo img, .brand-logo img')
                details['Brand'] = bimg['alt'].strip() if bimg and bimg.has_attr('alt') else None
                mdl = soup.select_one('.sku, .product-sku')
                details['Model'] = mdl.get_text(strip=True) if mdl else None
                desc = soup.select_one('#productDescription, .prodDesc, .longdesc, .shortDescription')
                if desc:
                    ps = desc.find_all('p')
                    details['Description'] = ' '.join(p.get_text(strip=True) for p in ps) if ps else desc.get_text(' ', strip=True)
                source = 'HTML scrape'
        except Exception:
            pass

    # 3. Additional API tests (e.g., BazaarVoice)
    try:
        rv_url = "https://api.bazaarvoice.com/data/reviews.json"
        rv_params = {
            "apiversion": "5.4",
            "Include": "Products,Stats",
            "limit": 1,
            "passkey": "7ezgnan69w4utwmyum0qtdl6u",
            "filter": f"ProductId:eq:{sku}",
            "sort": "Helpfulness:desc",
            "offset": 0
        }
        rv = requests.get(rv_url, params=rv_params, timeout=5).json()
        top = rv.get('Results', [])
        if top:
            details['TopReview'] = top[0].get('ReviewText')
    except Exception:
        pass

    # Display results
    st.subheader("Results")
    if details:
        for k, v in details.items():
            st.write(f"**{k}:** {v or 'n/a'}")
        st.caption(f"(Source: {source or 'multiple methods'})")
    else:
        st.error("Unable to retrieve data for that SKU from available sources.")

    # 4. Test additional endpoints and show raw responses
    st.markdown("---")
    st.subheader("Raw Endpoint Tests")
    endpoints = {
        "Bought Together Sets": "https://www.ajmadison.com/papi/packages/bought-together-sets/index.json.php",
        "Cart Index": "https://www.ajmadison.com/cart/cart.index.json.php",
        "Product List": "https://www.ajmadison.com/papi/products/list.json.php",
        "BazaarVoice Reviews": rv_url,
    }
    for name, ep in endpoints.items():
        try:
            if name == "BazaarVoice Reviews":
                r = requests.get(ep, params=rv_params, timeout=5)
            else:
                r = requests.get(ep, timeout=5)
            status = r.status_code
            content = r.text[:500] + ('...' if len(r.text) > 500 else '')
        except Exception as e:
            status = 'ERROR'
            content = str(e)
        st.write(f"**{name}** (Status: {status})")
        st.code(content, language='json')
