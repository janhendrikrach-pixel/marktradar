import json
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.aldi-nord.de"
START_URL = f"{BASE_URL}/sortiment.html"
OUTPUT = Path(__file__).resolve().parent / "aldi_sortiment.json"


def category_url(value):
    """Nur Sortimentsseiten akzeptieren und URLs vereinheitlichen."""
    if not isinstance(value, str):
        return None

    parsed = urlparse(urljoin(BASE_URL, value))

    if parsed.hostname != "www.aldi-nord.de":
        return None

    path = parsed.path.rstrip("/")
    if path != "/sortiment.html" and not path.startswith("/sortiment/"):
        return None

    if not path.endswith(".html"):
        # Andere Dateiformate und Produktdetailseiten ausschließen
        if "." in path.rsplit("/", 1)[-1]:
            return None
        path += ".html"

    return f"{BASE_URL}{path}"


def find_category_urls(value):
    """Auch JSON-Zeichenketten wie apiData auswerten."""
    if isinstance(value, dict):
        for child in value.values():
            yield from find_category_urls(child)
    elif isinstance(value, list):
        for child in value:
            yield from find_category_urls(child)
    elif isinstance(value, str):
        stripped = value.strip()

        if stripped.startswith(("[", "{")):
            try:
                yield from find_category_urls(json.loads(stripped))
            except json.JSONDecodeError:
                pass
        elif stripped.startswith(("/sortiment/", f"{BASE_URL}/sortiment/")):
            url = category_url(stripped)
            if url:
                yield url


def load_page(session, url):
    response = session.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if script is None:
        raise RuntimeError("Keine __NEXT_DATA__ gefunden")

    props = json.loads(script.get_text())["props"]["pageProps"]

    links = set(find_category_urls(props))
    for anchor in soup.select("a[href]"):
        url_candidate = category_url(anchor["href"])
        if url_candidate:
            links.add(url_candidate)

    return props, links


def main():
    queue = deque([START_URL])
    scheduled = {START_URL}
    products = {}
    pages = []
    errors = []

    with requests.Session() as session:
        while queue:
            url = queue.popleft()
            print(f"Abruf: {url}", flush=True)

            try:
                props, links = load_page(session, url)
                page_ids = set()
                checks = []

                indices = (
                    (props.get("algoliaState") or {})
                    .get("initialResults") or {}
                )

                for index_name, index_data in indices.items():
                    for result in index_data.get("results", []):
                        if "hits" not in result:
                            continue

                        hits = result["hits"]
                        total = result.get("nbHits")
                        checks.append({
                            "index": index_name,
                            "expected": total,
                            "received": len(hits),
                            "complete": (
                                total is not None and len(hits) == total
                            ),
                        })

                        for product in hits:
                            if "objectID" not in product or "name" not in product:
                                continue

                            product_id = str(product["objectID"])
                            page_ids.add(product_id)

                            if product_id not in products:
                                products[product_id] = {
                                    "data": product,
                                    "source_urls": [],
                                }

                            sources = products[product_id]["source_urls"]
                            if url not in sources:
                                sources.append(url)

                pages.append({
                    "url": url,
                    "product_count": len(page_ids),
                    "result_checks": checks,
                })

                print(f"  {len(page_ids)} Produkte")
                for check in checks:
                    if not check["complete"]:
                        print(
                            "  UNVOLLSTÄNDIG:",
                            check["received"],
                            "von",
                            check["expected"],
                        )

                for link in sorted(links):
                    if link not in scheduled:
                        scheduled.add(link)
                        queue.append(link)

            except (requests.RequestException, ValueError,
                    KeyError, TypeError, RuntimeError) as exc:
                errors.append({"url": url, "error": str(exc)})
                print(f"  FEHLER: {exc}")

            time.sleep(1)

    records = [
        {
            "id": product_id,
            "source_urls": entry["source_urls"],
            "data": entry["data"],
        }
        for product_id, entry in sorted(products.items())
    ]

    with_price = sum(
        (record["data"].get("currentPrice") or {}).get("priceValue")
        is not None
        for record in records
    )

    incomplete = sum(
        not check["complete"]
        for page in pages
        for check in page["result_checks"]
    )

    output = {
        "retailer": "ALDI Nord",
        "scope": "Öffentliches Website-Sortiment; keine Filialbestätigung",
        "currency": "EUR",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "pages_processed": len(pages),
            "products": len(records),
            "products_with_price": with_price,
            "incomplete_results": incomplete,
            "errors": len(errors),
        },
        "pages": pages,
        "errors": errors,
        "products": records,
    }

    # Erst vollständig schreiben, dann die bisherige Datei ersetzen.
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(OUTPUT)

    print("\nErgebnis:")
    print("Erfolgreich gelesene Seiten:", len(pages))
    print("Unterschiedliche Produkte:", len(records))
    print("Davon mit Preis:", with_price)
    print("Unvollständige Suchergebnisse:", incomplete)
    print("Fehler:", len(errors))
    print("Gespeichert:", OUTPUT)


if __name__ == "__main__":
    main()