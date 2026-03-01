import requests
import json

BASE_URL = "http://localhost:8763"

# Test futures RESTful API endpoints
def test_futures_rest_api():
    print("Testing futures RESTful API endpoints...")
    
    # Test 1: Get order book depth
    print("\n1. Testing order book depth...")
    symbols = ["BTCUSDT", "ETHUSDT", "JPMUSDT"]
    for symbol in symbols:
        response = requests.get(f"{BASE_URL}/fapi/v1/depth", params={"symbol": symbol})
        print(f"{symbol}: {response.status_code} - {response.json()}")
    
    # Test 2: Get ticker price
    print("\n2. Testing ticker price...")
    for symbol in symbols:
        response = requests.get(f"{BASE_URL}/fapi/v1/ticker/price", params={"symbol": symbol})
        print(f"{symbol}: {response.status_code} - {response.json()}")
    
    # Test 3: Get klines
    print("\n3. Testing klines...")
    intervals = ["1m", "1h", "1d"]
    for symbol in symbols:
        for interval in intervals:
            response = requests.get(f"{BASE_URL}/fapi/v1/klines", params={
                "symbol": symbol,
                "interval": interval,
                "limit": 5
            })
            data = response.json().get('data', [])
            print(f"{symbol} {interval}: {response.status_code} - {len(data)} klines")
    
    # Test 4: Get trades
    print("\n4. Testing trades...")
    for symbol in symbols:
        response = requests.get(f"{BASE_URL}/fapi/v1/trades", params={
            "symbol": symbol,
            "limit": 10
        })
        data = response.json().get('data', [])
        print(f"{symbol}: {response.status_code} - {len(data)} trades")
    
    # Test 5: Test error handling for invalid symbol
    print("\n5. Testing error handling for invalid symbol...")
    response = requests.get(f"{BASE_URL}/fapi/v1/depth", params={"symbol": "INVALID"})
    print(f"Invalid symbol: {response.status_code} - {response.json()}")
    
    # Test 6: Test error handling for invalid interval
    print("\n6. Testing error handling for invalid interval...")
    response = requests.get(f"{BASE_URL}/fapi/v1/klines", params={
        "symbol": "BTCUSDT",
        "interval": "invalid"
    })
    print(f"Invalid interval: {response.status_code} - {response.json()}")
    
    # Test 7: Test futures private API endpoints
    print("\n7. Testing futures private API endpoints...")
    
    # Test 7.1: Create a new order
    print("\n7.1 Testing new order creation...")
    order_data = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "LIMIT",
        "quantity": "1.0",
        "price": "59000.0"
    }
    response = requests.post(f"{BASE_URL}/fapi/v1/order", json=order_data)
    print(f"New order: {response.status_code} - {response.json()}")
    
    # Test 7.2: Create batch orders
    print("\n7.2 Testing batch order creation...")
    batch_data = {
        "batchOrders": [
            {
                "symbol": "ETHUSDT",
                "side": "BUY",
                "type": "LIMIT",
                "quantity": "10.0",
                "price": "3500.0"
            },
            {
                "symbol": "ETHUSDT",
                "side": "SELL",
                "type": "LIMIT",
                "quantity": "5.0",
                "price": "3600.0"
            }
        ]
    }
    response = requests.post(f"{BASE_URL}/fapi/v1/batchOrders", json=batch_data)
    print(f"Batch orders: {response.status_code} - {len(response.json().get('data', []))} orders created")
    
    # Test 7.3: Get open orders
    print("\n7.3 Testing get open orders...")
    response = requests.get(f"{BASE_URL}/fapi/v1/openOrders?symbol=BTCUSDT")
    print(f"Open orders: {response.status_code} - {response.json().get('data', [])}")
    
    # Test 7.4: Cancel orders
    print("\n7.4 Testing cancel orders...")
    open_orders = response.json().get('data', [])
    if open_orders:
        order_ids = [order['orderId'] for order in open_orders[:2]]  # Cancel first 2 orders
        order_ids_str = ','.join(order_ids)
        response = requests.delete(f"{BASE_URL}/fapi/v1/order", params={
            "symbol": "BTCUSDT",
            "orderIds": order_ids_str
        })
        print(f"Cancel orders: {response.status_code} - {response.json()}")
    else:
        print("No open orders to cancel")
    
    # Test 7.5: Mock trade
    print("\n7.5 Testing mock trade...")
    mock_data = {
        "symbol": "JPMUSDT",
        "price": "59000.0",
        "quantity": "0.5"
    }
    response = requests.post(f"{BASE_URL}/fapi/v3/mock", json=mock_data)
    print(f"Mock trade: {response.status_code} - {response.json()}")
    
    print("\nFutures RESTful API tests completed!")

if __name__ == "__main__":
    test_futures_rest_api()
