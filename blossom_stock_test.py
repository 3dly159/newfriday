import os
import requests
import sys
from datetime import datetime
import json
import urllib.request
import urllib.error

BASE_URL = os.getenv("BLOSSOM_API_URL", "http://81.10.121.99:81/api")
TOKEN = os.getenv("BLOSSOM_TOKEN")
HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

def fetch(endpoint):
    url = f"{BASE_URL}{endpoint}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error: {e}")
        sys.exit(2)
    except requests.exceptions.Timeout as e:
        print(f"Timeout error: {e}")
        sys.exit(3)
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e}")
        sys.exit(4)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

def fetch_json(url, token=None):
    req = urllib.request.Request(url)
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(req) as response:
            data = response.read().decode('utf-8')
            return json.loads(data)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def fetch_text(url):
    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode('utf-8').strip()
    except Exception as e:
        print(f"Error fetching text {url}: {e}")
        return None

def main():
    try:
        token_url = f"{BASE_URL}/Users/Token/1"
        TOKEN = fetch_text(token_url)
        if not TOKEN:
            print("Failed to retrieve token")
            return
        print("Token acquired (length:", len(TOKEN), ")")
        HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
        supplies = fetch_json(f"{BASE_URL}/SupplyDetail/GetAll", TOKEN)
        transactions = fetch_json(f"{BASE_URL}/TransactionDetail/GetAll", TOKEN)
        actual_stock = fetch_json(f"{BASE_URL}/ProductLocationStock/GetAll", TOKEN)
        products = fetch_json(f"{BASE_URL}/Product/GetAll", TOKEN)
    except SystemExit:
        raise
    except Exception as e:
        print(f"Failed to fetch data: {e}")
        sys.exit(1)

    # Build product ID -> name map
    product_name = {p.get("productID"): p.get("name", "Unknown") for p in products}

    # Log products to file
    log_file = "stock_test_results.log"
    with open(log_file, "a") as f:
        f.write(f"\n=== Stock Test Run at {datetime.now().isoformat()} ===\n")
        f.write("Product ID, Product Name\n")
        for pid, name in product_name.items():
            f.write(f"{pid}, {name}\n")

    # Compute supply sums (product only, as location not in supply detail)
    supply_sum = {}
    for s in supplies:
        pid = s.get("product_ID")
        qty = s.get("quantity", 0)
        supply_sum[pid] = supply_sum.get(pid, 0) + qty

    # Compute transaction sums (outgoing)
    trans_sum = {}
    for t in transactions:
        pid = t.get("productID")
        qty = t.get("quantity", 0)
        trans_sum[pid] = trans_sum.get(pid, 0) + qty

    expected = {}
    for pid, total in supply_sum.items():
        expected[pid] = total - trans_sum.get(pid, 0)
    for pid, total in trans_sum.items():
        if pid not in expected:
            expected[pid] = -total

    # Build actual dict (product only, sum across locations)
    actual = {}
    for a in actual_stock:
        pid = a.get("productID")
        qty = a.get("quantity", 0)
        actual[pid] = actual.get(pid, 0) + qty

    # Compare
    mismatches = []
    all_keys = set(expected.keys()) | set(actual.keys())
    for pid in all_keys:
        exp = expected.get(pid, 0)
        act = actual.get(pid, 0)
        if exp != act:
            mismatches.append((pid, exp, act))

    if mismatches:
        print("Mismatches found (productID, expected, actual):")
        for pid, exp, act in mismatches:
            name = product_name.get(pid, "Unknown")
            print(f"{pid} ({name}): expected {exp}, actual {act}")
        # Also log mismatches to file
        with open(log_file, "a") as f:
            f.write("\nMISMATCHES:\n")
            for pid, exp, act in mismatches:
                name = product_name.get(pid, "Unknown")
                f.write(f"{pid} ({name}): expected {exp}, actual {act}\n")
        sys.exit(1)
    else:
        print("Stock consistency check passed.")
        with open(log_file, "a") as f:
            f.write("Stock consistency check passed.\n")
        sys.exit(0)

if __name__ == "__main__":
    main()