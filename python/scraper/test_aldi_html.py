import json

import requests
from bs4 import BeautifulSoup

url = (
    "https://www.aldi-nord.de/sortiment/"
    "milchprodukte/milch-milchgetraenke.html"
)

response = requests.get(url, timeout=30)
print("HTTP-Status:", response.status_code)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
script = soup.find("script", id="__NEXT_DATA__")

if script is None:
    print("Keine eingebetteten Next.js-Daten gefunden.")
else:
    data = json.loads(script.get_text())
    print("Build-ID:", data.get("buildId"))

    indices = (
        data.get("props", {})
        .get("pageProps", {})
        .get("algoliaState", {})
        .get("initialResults", {})
    )

    if not indices:
        print("Keine eingebetteten Suchergebnisse gefunden.")

    for index_name, index_data in indices.items():
        for result in index_data.get("results", []):
            print("Index:", index_name)
            print("Treffer insgesamt:", result.get("nbHits"))
            print("Gelieferte Produkte:", len(result.get("hits", [])))