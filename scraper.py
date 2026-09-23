import requests
from bs4 import BeautifulSoup
import psycopg2
from datetime import datetime

# 1. Trage HIER deinen kopierten Link ein (Passwort nicht vergessen!)
DB_URI = "postgresql://postgres.srlhhscoumlvojawyiqm:Keinersolleswissen1991!@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

def fetch_data(search_term):
    print(f"🔥 Feuere Live-Anfrage an REWE API für '{search_term}'...")
    
    # Deine gefundene API (mit dynamischem Suchbegriff)
    url = f"https://www.rewe.de/shop/api/products?term={search_term}&autoCompletion=true&objectsPerPage=5&marketId=541793&serviceType=PICKUP"
    
    # Wir tun so, als wären wir ein normaler Chrome-Browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    
    results = []
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            print("✅ BINGO! Die REWE-API hat Daten geschickt.")
            data = response.json()
            
            # REWE verschachtelt die Produktdaten in der API-Antwort oft unter '_embedded' -> 'products'
            # (Wir fangen das defensiv ab, falls sie die Struktur leicht ändern)
            products = data.get('_embedded', {}).get('products', [])
            
            # Falls die Struktur anders ist, versuchen wir es direkt:
            if not products and isinstance(data, list):
                products = data
            elif not products and 'products' in data:
                products = data['products']
                
            # HIER IST DIE NEUERUNG: Wir drucken das erste Produkt roh aus!
            if len(products) > 0:
                print("\n--- 🔍 HIER IST DAS ROHE PAKET VON REWE ---")
                print(products[0])
                print("-------------------------------------------\n")

            for prod in products:
                try:
                    # 1. Den echten Namen auslesen
                    name = prod.get('productName', 'Unbekannt')
                    
                    # 2. Die Marke auslesen (falls vorhanden)
                    brand = "Unbekannt"
                    if 'brand' in prod and 'name' in prod['brand']:
                        brand = prod['brand']['name']
                        
                    # 3. Tief in den REWE-Tresor für Preis und EAN greifen
                    articles = prod.get('_embedded', {}).get('articles', [])
                    if not articles:
                        continue # Wenn kein Artikel drin ist, überspringen wir es
                        
                    article = articles[0]
                    
                    # Die EAN heißt bei REWE "gtin"
                    ean = article.get('gtin', f"DUMMY_{name[:5]}")
                    
                    # Der Preis in Cent (z.B. 109 für 1.09€)
                    price_cents = article.get('_embedded', {}).get('listing', {}).get('pricing', {}).get('currentRetailPrice', 0)
                    price = price_cents / 100.0 # Wir teilen durch 100 für Euro!
                    
                    results.append({
                        "ean": ean,
                        "name": name,
                        "brand": brand,
                        "price": price,
                        "is_on_sale": False
                    })
                except Exception as e:
                    print(f"Fehler beim Lesen eines Produkts: {e}")
                    
            print(f"-> {len(results)} echte Produkte aus der API extrahiert!")
            
        else:
            print(f"❌ REWE blockiert (Status: {response.status_code}). Versuche später erneut.")
            
    except Exception as e:
        print(f"❌ Fehler beim API-Abruf: {e}")

    # Wir geben unsere extrahierten API-Daten an die Datenbank-Funktion weiter
    return {"results": results}

def process_and_save_data(json_data, db_store_id):
    try:
        print("Verbinde mit Supabase Datenbank...")
        conn = psycopg2.connect(DB_URI)
        cursor = conn.cursor()
        
        for item in json_data.get('results', []):
            ean = item['ean']
            name = item['name']
            brand = item['brand']
            price = item['price']
            is_discount = item['is_on_sale']
            
            print(f"Speichere: {name} für {price} €")
            
            # Produkt in DB schreiben (verhindert Duplikate via EAN)
            cursor.execute("""
                INSERT INTO products (ean_barcode, name, brand) 
                VALUES (%s, %s, %s)
                ON CONFLICT (ean_barcode) DO NOTHING
                RETURNING id;
            """, (ean, name, brand))
            
            product_id_row = cursor.fetchone()
            if not product_id_row:
                cursor.execute("SELECT id FROM products WHERE ean_barcode = %s", (ean,))
                product_id_row = cursor.fetchone()
                
            product_id = product_id_row[0]
            
            # Preis in DB schreiben
            cursor.execute("""
                INSERT INTO prices (product_id, store_id, current_price, is_discount, updated_at) 
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (product_id, store_id) 
                DO UPDATE SET 
                    current_price = EXCLUDED.current_price,
                    is_discount = EXCLUDED.is_discount,
                    updated_at = EXCLUDED.updated_at;
            """, (product_id, db_store_id, price, is_discount, datetime.now()))
            
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ ERFOLG: Alle Daten wurden in Supabase gespeichert!")
        
    except Exception as e:
        print("❌ FEHLER bei der Datenbankverbindung:", e)

if __name__ == "__main__":
    data = fetch_data("Milch")
    process_and_save_data(data, db_store_id=1)