import json
import time

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.aldi-nord.de"
START_URL = f"{BASE_URL}/sortiment/milchprodukte.html"


def load_page_props(session, url):
    response = session.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")

    if script is None:
        raise RuntimeError(f"Keine __NEXT_DATA__: {url}")

    return json.loads(script.get_text())["props"]["pageProps"]


with requests.Session() as session:
    props = load_page_props(session, START_URL)

    api_data = props.get("apiData", [])
    if isinstance(api_data, str):
        api_data = json.loads(api_data)

    categories = {}
    for operation, payload in api_data:
        if operation == "PRODUCT_MGNL_CATEGORY_CHILDREN_GET":
            for category in payload.get("res", []):
                path = category["reference"]["path"]
                url = f"{BASE_URL}{path}.html"
                categories[url] = category["navigationTitle"].strip()

    if not categories:
        raise RuntimeError("Keine Unterkategorien gefunden.")

    products = {}
    incomplete = []

    for url, title in categories.items():
        time.sleep(1)
        props = load_page_props(session, url)
        indices = (
            props.get("algoliaState", {})
            .get("initialResults", {})
        )

        category_ids = set()
        found_results = False

        for index_data in indices.values():
            for result in index_data.get("results", []):
                if "hits" not in result:
                    continue

                found_results = True
                hits = result["hits"]
                total = result.get("nbHits")

                if total is None or len(hits) != total:
                    incomplete.append(title)

                for product in hits:
                    product_id = str(product["objectID"])
                    category_ids.add(product_id)
                    products[product_id] = product

        if not found_results:
            incomplete.append(title)

        print(f"{title}: {len(category_ids)} Produkte")

    print(f"\nUnterschiedliche Produkte insgesamt: {len(products)}")
    print(
        "Davon mit Preis:",
        sum(
            product.get("currentPrice", {}).get("priceValue") is not None
            for product in products.values()
        ),
    )

    if incomplete:
        print(
            "Nicht vollständig bestätigt:",
            ", ".join(sorted(set(incomplete))),
        )

    print()
    for product in sorted(
        products.values(),
        key=lambda item: item.get("name", "").strip().casefold(),
    ):
        print(
            product["objectID"],
            product.get("name", "").strip(),
            product.get("salesUnit"),
            product.get("currentPrice", {}).get("priceValue"),
            sep=" | ",
        )