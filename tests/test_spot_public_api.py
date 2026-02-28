import requests
import json

BASE_URL = "http://localhost:8763"

# Test spot public API endpoints
def test_spot_public_api():
    print("Testing spot public API endpoints...")
    
    # Test 1: Get order book depth
    print("\n1. Testing order book depth...")
    symbols = ["BTCUSDT", "ETHUSDT", "JPMUSDT"]
    for symbol in symbols:
        response = requests.get(f"{BASE_URL}/api/v3/depth", params={"symbol": symbol})
        print(f"{symbol}: {response.status_code} - {response.json()}")
    
    # Test 2: Get ticker price
    print("\n2. Testing ticker price...")
    for symbol in symbols:
        response = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={"symbol": symbol})
        print(f"{symbol}: {response.status_code} - {response.json()}")
    
    # Test 3: Get klines
    print("\n3. Testing klines...")
    intervals = ["1m", "1h", "1d"]
    for symbol in symbols:
        for interval in intervals:
            response = requests.get(f"{BASE_URL}/api/v3/klines", params={
                "symbol": symbol,
                "interval": interval,
                "limit": 5
            })
            data = response.json().get('data', [])
            print(f"{symbol} {interval}: {response.status_code} - {len(data)} klines")
    
    # Test 4: Get trades
    print("\n4. Testing trades...")
    for symbol in symbols:
        response = requests.get(f"{BASE_URL}/api/v3/trades", params={
            "symbol": symbol,
            "limit": 10
        })
        data = response.json().get('data', [])
        print(f"{symbol}: {response.status_code} - {len(data)} trades")
    
    # Test 5: Test error handling for invalid symbol
    print("\n5. Testing error handling for invalid symbol...")
    response = requests.get(f"{BASE_URL}/api/v3/depth", params={"symbol": "INVALID"})
    print(f"Invalid symbol: {response.status_code} - {response.json()}")
    
    # Test 6: Test error handling for invalid interval
    print("\n6. Testing error handling for invalid interval...")
    response = requests.get(f"{BASE_URL}/api/v3/klines", params={
        "symbol": "BTCUSDT",
        "interval": "invalid"
    })
    print(f"Invalid interval: {response.status_code} - {response.json()}")
    
    print("\nSpot public API tests completed!")

if __name__ == "__main__":
    test_spot_public_api()
