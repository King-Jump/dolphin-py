import requests
import json

BASE_URL = "http://localhost:8763"

# Test spot private API endpoints
def test_spot_private_api():
    print("Testing spot private API endpoints...")
    
    # Test 1: Create a new order
    print("\n1. Testing new order creation...")
    order_data = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "LIMIT",
        "quantity": "1.0",
        "price": "59000.0"
    }
    response = requests.post(f"{BASE_URL}/api/v3/order", json=order_data)
    print(f"New order: {response.status_code} - {response.json()}")
    
    # Test 2: Create batch orders
    print("\n2. Testing batch order creation...")
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
    response = requests.post(f"{BASE_URL}/api/v3/batchOrders", json=batch_data)
    print(f"Batch orders: {response.status_code} - {len(response.json().get('data', []))} orders created")
    
    # Test 3: Get open orders
    print("\n3. Testing get open orders...")
    response = requests.get(f"{BASE_URL}/api/v3/openOrders?symbol=BTCUSDT")
    print(f"Open orders: {response.status_code} - {response.json().get('data', [])}")
    
    # Test 4: Cancel orders (need order IDs from previous response)
    print("\n4. Testing cancel orders...")
    open_orders = response.json().get('data', [])
    if open_orders:
        order_ids = [order['orderId'] for order in open_orders[:2]]  # Cancel first 2 orders
        order_ids_str = ','.join(order_ids)
        response = requests.delete(f"{BASE_URL}/api/v3/order", params={
            "symbol": "BTCUSDT",
            "orderIds": order_ids_str
        })
        print(f"Cancel orders: {response.status_code} - {response.json()}")
    else:
        print("No open orders to cancel")
    
    # Test 5: Mock trade
    print("\n5. Testing mock trade...")
    mock_data = {
        "symbol": "BTCUSDT",
        "price": "59000.0",
        "quantity": "0.5"
    }
    response = requests.post(f"{BASE_URL}/api/v3/mock", json=mock_data)
    print(f"Mock trade: {response.status_code} - {response.json()}")
    
    print("\nSpot private API tests completed!")

    # Test 6: Self trade
    print("\n6. Testing self trade...")
    batch_data = {
        "batchOrders": [
            {
                "symbol": "JPMUSDT",
                "side": "BUY",
                "type": "LIMIT",
                "quantity": "10.0",
                "price": "100.0"
            },
            {
                "symbol": "JPMUSDT",
                "side": "SELL",
                "type": "LIMIT",
                "quantity": "5.0",
                "price": "100.0"
            }
        ]
    }
    response = requests.post(f"{BASE_URL}/api/v3/batchOrders", json=batch_data)
    print(f"Self trade: {response.status_code} - {response.json().get('data', [])}")

if __name__ == "__main__":
    test_spot_private_api()
