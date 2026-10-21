import json

import requests
from bs4 import BeautifulSoup

url = "https://www.aldi-nord.de/sortiment/milchprodukte.html"

response = requests.get(url, timeout=30)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
script = soup.find("script", id="__NEXT_DATA__")

if script is None:
    raise RuntimeError("Keine __NEXT_DATA__ gefunden.")

data = json.loads(script.get_text())
props = data["props"]["pageProps"]

api_data = props.get("apiData", [])

if isinstance(api_data, str):
    api_data = json.loads(api_data)

for operation, payload in api_data:
    if operation == "PRODUCT_MGNL_CATEGORY_CHILDREN_GET":
        for category in payload.get("res", []):
            path = category["reference"]["path"]
            category_url = f"https://www.aldi-nord.de{path}.html"
            print(category["navigationTitle"].strip())
            print(category_url)
            print()