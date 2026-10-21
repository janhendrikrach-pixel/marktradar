import requests
from bs4 import BeautifulSoup

url = "https://www.penny.de/angebote"

response = requests.get(url)

print("Statuscode: ", response.status_code)
print("Finale URL: ", response.url)
print("Content-Type: ", response.headers.get("Content-Type"))
print("Zeichen im HTML: ", len(response.text))

soup = BeautifulSoup(response.text, "html.parser")

if soup.title:
    print("Seitentitel: ", soup.title.get_text(strip=True))
else:
    print("Seitentitel: keiner")

print("\nErste 500 Zeichen des sichtbaren Textes: ")
print(soup.get_text(" ", strip=True)[:500])