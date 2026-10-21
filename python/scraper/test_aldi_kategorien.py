import json

import requests
from bs4 import BeautifulSoup

url = "https://www.aldi-nord.de/sortiment/milchprodukte.html"

response = requests.get(url, timeout=30)
print("HTTP-Status:", response.status_code)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
links = set()

# Links im HTML — ohne Einschränkung auf ".html"
for anchor in soup.select("a[href]"):
    href = anchor["href"]
    if "/sortiment/" in href:
        links.add(href)

# Verweise in eingebetteten Next.js-Daten
script = soup.find("script", id="__NEXT_DATA__")

def find_links(value):
    if isinstance(value, dict):
        for child in value.values():
            find_links(child)
    elif isinstance(value, list):
        for child in value:
            find_links(child)
    elif isinstance(value, str) and "/sortiment/" in value:
        # Lange redaktionelle Texte nicht ausgeben
        if len(value) < 500:
            links.add(value)

if script is not None:
    find_links(json.loads(script.get_text()))
else:
    print("Keine __NEXT_DATA__ gefunden.")

print("Gefundene Sortimentsverweise:", len(links))

for link in sorted(links):
    print(link)