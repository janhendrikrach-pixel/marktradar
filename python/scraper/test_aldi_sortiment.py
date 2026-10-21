import requests

url = (
    "https://www.aldi-nord.de/_next/data/"
    "Fj3ub-94bBCVyGJQMzOQX/de/sortiment/"
    "milchprodukte/milch-milchgetraenke.html.json"
)

response = requests.get(url, timeout=30)
print("HTTP-Status:", response.status_code)
response.raise_for_status()

data = response.json()
indices = data["pageProps"]["algoliaState"]["initialResults"]

for index_data in indices.values():
    for result in index_data["results"]:
        print("Treffer insgesamt:", result["nbHits"])
        print("Gelieferte Produkte:", len(result["hits"]))

        for product in result["hits"]:
            price = product.get("currentPrice", {}).get("priceValue")
            print(
                product["objectID"],
                product["name"].strip(),
                product.get("salesUnit"),
                price,
                sep=" | ",
            )