import json
import urllib.request
import urllib.error

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
    base = "http://81.10.121.99:81/api"
    token_url = f"{base}/Users/Token/1"
    token = fetch_text(token_url)
    if not token:
        print("Failed to retrieve token")
        return
    print("Token acquired (length:", len(token), ")")
    
    # Fetch supply details
    supply_url = f"{base}/SupplyDetail/GetAll"
    supply_data = fetch_json(supply_url, token)
    if supply_data is None:
        print("Failed to fetch supply data")
        return
    # Fetch transaction details
    trans_url = f"{base}/TransactionDetail/GetAll"
    trans_data = fetch_json(trans_url, token)
    if trans_data is None:
        print("Failed to fetch transaction data")
        return
    # Fetch product location stock
    stock_url = f"{base}/ProductLocationStock/GetAll"
    stock_data = fetch_json(stock_url, token)
    if stock_data is None:
        print("Failed to fetch stock data")
        return
    
    # Compute supply totals per product
    supply_totals = {}
    for item in supply_data:
        pid = item.get('product_ID')
        qty = item.get('quantity', 0)
        if pid is not None:
            supply_totals[pid] = supply_totals.get(pid, 0) + qty
    
    # Compute transaction totals per product
    trans_totals = {}
    for item in trans_data:
        pid = item.get('productID')
        qty = item.get('quantity', 0)
        if pid is not None:
            trans_totals[pid] = trans_totals.get(pid, 0) + qty
    
    # Compute expected stock (supply - transaction)
    expected = {}
    all_pids = set(supply_totals.keys()) | set(trans_totals.keys())
    for pid in all_pids:
        s = supply_totals.get(pid, 0)
        t = trans_totals.get(pid, 0)
        expected[pid] = s - t
    
    # Compute actual stock from ProductLocationStock (sum quantity per productID)
    actual = {}
    for item in stock_data:
        pid = item.get('productID')
        qty = item.get('quantity', 0)
        if pid is not None:
            actual[pid] = actual.get(pid, 0) + qty
    
    # Compare
    mismatches = []
    all_pids = set(expected.keys()) | set(actual.keys())
    for pid in all_pids:
        exp = expected.get(pid, 0)
        act = actual.get(pid, 0)
        if exp != act:
            mismatches.append((pid, exp, act))
    
    if mismatches:
        print("MISMATCHES FOUND:")
        for pid, exp, act in mismatches:
            print(f"Product ID {pid}: Expected {exp}, Actual {act}")
    else:
        print("All stocks match.")
    
    print(f"Total products in supply: {len(supply_totals)}")
    print(f"Total products in transactions: {len(trans_totals)}")
    print(f"Total products in stock: {len(actual)}")

if __name__ == '__main__':
    main()