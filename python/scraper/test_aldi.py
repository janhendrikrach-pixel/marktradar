import requests

url = (
    "https://www.aldi-nord.de/api/product/pds/"
    "6170%2C6149%2C6109%2C6216%2C1024345%2C6249%2C6186"
    "?scope=de"
)

response = requests.get(url, timeout=30)

print("HTTP-Status:", response.status_code)
print("Content-Type:", response.headers.get("Content-Type"))

response.raise_for_status()
data = response.json()

for product in data.get("products", []):
    price = product.get("currentPrice", {}).get("priceValue")
    print(
        product["objectID"],
        product["name"],
        product.get("salesUnit"),
        price,
        sep=" | ",
    )