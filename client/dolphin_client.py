import requests
import websocket
import json
import time
from typing import List, Dict, Any, Optional

class DolphinClient:
    def __init__(self, base_url: str = "http://localhost:8763", ws_url: str = "ws://localhost:8765"):
        self.base_url = base_url
        self.ws_url = ws_url
        self.ws = None
        self.ws_callbacks = {}
    
    # Spot API Methods
    def spot_new_order(self, symbol: str, side: str, order_type: str, quantity: str, price: Optional[str] = None, client_order_id: Optional[str] = None) -> Dict:
        url = f"{self.base_url}/api/v3/order"
        data = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity
        }
        if price:
            data["price"] = price
        if client_order_id:
            data["client_order_id"] = client_order_id
        response = requests.post(url, json=data)
        return response.json()
    
    def spot_batch_orders(self, batch_orders: List[Dict]) -> Dict:
        url = f"{self.base_url}/api/v3/batchOrders"
        data = {"batchOrders": batch_orders}
        response = requests.post(url, json=data)
        return response.json()
    
    def spot_cancel_orders(self, symbol: str, order_ids: str) -> Dict:
        url = f"{self.base_url}/api/v3/order"
        params = {
            "symbol": symbol,
            "orderIds": order_ids
        }
        response = requests.delete(url, params=params)
        return response.json()
    
    def spot_get_open_orders(self, symbol: Optional[str] = None) -> Dict:
        url = f"{self.base_url}/api/v3/openOrders"
        params = {}
        if symbol:
            params["symbol"] = symbol
        response = requests.get(url, params=params)
        return response.json()
    
    def spot_order_status(self, symbol: str, order_id: str) -> Dict:
        url = f"{self.base_url}/api/v3/order"
        params = {
            "symbol": symbol,
            "orderId": order_id
        }
        response = requests.get(url, params=params)
        return response.json()
    
    def spot_mock_trade(self, symbol: str, side: str, price: str, quantity: str) -> Dict:
        url = f"{self.base_url}/api/v3/mock"
        data = {
            "symbol": symbol,
            "side": side,
            "price": price,
            "quantity": quantity
        }
        response = requests.post(url, json=data)
        return response.json()
    
    def spot_get_depth(self, symbol: str, limit: Optional[int] = 30) -> Dict:
        url = f"{self.base_url}/api/v3/depth"
        params = {
            "symbol": symbol
        }
        if limit:
            params["limit"] = limit
        response = requests.get(url, params=params)
        return response.json()
    
    def spot_get_ticker_price(self, symbol: str) -> Dict:
        url = f"{self.base_url}/api/v3/ticker/price"
        params = {"symbol": symbol}
        response = requests.get(url, params=params)
        return response.json()
    
    def spot_get_klines(self, symbol: str, interval: Optional[str] = "1m", limit: Optional[int] = 10) -> Dict:
        url = f"{self.base_url}/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        response = requests.get(url, params=params)
        return response.json()
    
    # Futures API Methods
    def futures_new_order(self, symbol: str, side: str, order_type: str, quantity: str, price: Optional[str] = None, client_order_id: Optional[str] = None) -> Dict:
        url = f"{self.base_url}/fapi/v1/order"
        data = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity
        }
        if price:
            data["price"] = price
        if client_order_id:
            data["client_order_id"] = client_order_id
        response = requests.post(url, json=data)
        return response.json()
    
    def futures_batch_orders(self, batch_orders: List[Dict]) -> Dict:
        url = f"{self.base_url}/fapi/v1/batchOrders"
        data = {"batchOrders": batch_orders}
        response = requests.post(url, json=data)
        return response.json()
    
    def futures_cancel_orders(self, symbol: str, order_ids: str) -> Dict:
        url = f"{self.base_url}/fapi/v1/order"
        params = {
            "symbol": symbol,
            "orderIds": order_ids
        }
        response = requests.delete(url, params=params)
        return response.json()
    
    def futures_get_open_orders(self, symbol: Optional[str] = None) -> Dict:
        url = f"{self.base_url}/fapi/v1/openOrders"
        params = {}
        if symbol:
            params["symbol"] = symbol
        response = requests.get(url, params=params)
        return response.json()
    
    def futures_order_status(self, symbol: str, order_id: str) -> Dict:
        url = f"{self.base_url}/fapi/v1/order"
        params = {
            "symbol": symbol,
            "orderId": order_id
        }
        response = requests.get(url, params=params)
        return response.json()
    
    def futures_mock_trade(self, symbol: str, side: str, price: str, quantity: str) -> Dict:
        url = f"{self.base_url}/fapi/v3/mock"
        data = {
            "symbol": symbol,
            "side": side,
            "price": price,
            "quantity": quantity
        }
        response = requests.post(url, json=data)
        return response.json()
    
    def futures_get_depth(self, symbol: str, limit: Optional[int] = 30) -> Dict:
        url = f"{self.base_url}/fapi/v1/depth"
        params = {
            "symbol": symbol
        }
        if limit:
            params["limit"] = limit
        response = requests.get(url, params=params)
        return response.json()
    
    def futures_get_ticker_price(self, symbol: str) -> Dict:
        url = f"{self.base_url}/fapi/v1/ticker/price"
        params = {"symbol": symbol}
        response = requests.get(url, params=params)
        return response.json()
    
    def futures_get_klines(self, symbol: str, interval: Optional[str] = "1m", limit: Optional[int] = 10) -> Dict:
        url = f"{self.base_url}/fapi/v1/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        response = requests.get(url, params=params)
        return response.json()
    
    # WebSocket Methods
    def _on_message(self, ws, message):
        data = json.loads(message)
        if "e" in data:
            event_type = data["e"]
            symbol = data["s"]
            if event_type in self.ws_callbacks:
                for callback in self.ws_callbacks[event_type]:
                    callback(data)
    
    def _on_error(self, ws, error):
        print(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        print(f"WebSocket closed: {close_status_code} - {close_msg}")
    
    def _on_open(self, ws):
        print("WebSocket connected")
    
    def connect_ws(self, path: str = "/spot"):
        """Connect to WebSocket with specified path ("/spot" or "/future")"""
        full_url = f"{self.ws_url}{path}"
        self.ws = websocket.WebSocketApp(
            full_url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
        import threading
        threading.Thread(target=self.ws.run_forever, daemon=True).start()
        time.sleep(1)  # Give time for connection to establish
    
    def subscribe(self, params: List[str], id: int = 1):
        """Subscribe to WebSocket streams
        Example params: ["btcusdt@depth", "btcusdt@trade"]
        """
        if not self.ws:
            raise Exception("WebSocket not connected")
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": params,
            "id": id
        }
        self.ws.send(json.dumps(subscribe_message))
    
    def register_callback(self, event_type: str, callback):
        """Register callback for WebSocket events
        Event types: "depthUpdate", "trade"
        """
        if event_type not in self.ws_callbacks:
            self.ws_callbacks[event_type] = []
        self.ws_callbacks[event_type].append(callback)
    
    def close_ws(self):
        if self.ws:
            self.ws.close()
            self.ws = None

if __name__ == "__main__":
    # Example usage
    client = DolphinClient()
    
    # Test spot public API
    print("Testing spot public API...")
    depth = client.spot_get_depth("BTCUSDT")
    print(f"Order book depth: {depth}")
    
    ticker = client.spot_get_ticker_price("BTCUSDT")
    print(f"Latest price: {ticker}")
    
    klines = client.spot_get_klines("BTCUSDT", interval="1m", limit=5)
    print(f"Kline data: {klines}")
    
    # Test WebSocket
    print("\nTesting WebSocket...")
    def on_depth_update(data):
        print(f"Depth update: {data}")
    
    def on_trade(data):
        print(f"Trade update: {data}")
    
    client.connect_ws("/spot")
    client.register_callback("depthUpdate", on_depth_update)
    client.register_callback("trade", on_trade)
    client.subscribe(["btcusdt@depth", "btcusdt@trade"])
    
    # Keep program running to receive WebSocket messages
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        client.close_ws()
        print("Client stopped")
