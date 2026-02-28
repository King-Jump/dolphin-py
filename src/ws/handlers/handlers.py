import asyncio
import json
import time
from src.engine.orderbook.orderbook import OrderBook

class WebSocketHandler:
    def __init__(self):
        self.orderbook = OrderBook()
        # support small size of web sockets
        self.client_max_size = 3
        self.clients = []
    
    async def handle_connection(self, websocket, path):
        if len(self.clients) >= self.client_max_size:
            self.clients.pop()
            self.clients.append(websocket)
        try:
            # Parse subscription request
            async for message in websocket:
                data = json.loads(message)
                if data.get('method') == 'SUBSCRIBE':
                    params = data.get('params', [])
                    await self.handle_subscription(websocket, params)
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            self.clients.remove(websocket)
    
    async def handle_subscription(self, websocket, params):
        for param in params:
            if 'depth' in param:
                symbol = param.split('@')[0]
                await self.send_depth_updates(websocket, symbol)
            elif 'ticker' in param:
                symbol = param.split('@')[0]
                await self.send_ticker_updates(websocket, symbol)
    
    async def send_depth_updates(self, websocket, symbol):
        while websocket in self.clients:
            try:
                depth = self.orderbook.get_depth(symbol, 30)
                update = {
                    "e": "depthUpdate",
                    "E": int(time.time() * 1000),
                    "s": symbol,
                    "U": depth.get('lastUpdateId', 0),
                    "u": depth.get('lastUpdateId', 0),
                    "b": depth.get('bids', []),
                    "a": depth.get('asks', [])
                }
                await websocket.send(json.dumps(update))
                await asyncio.sleep(0.2)  # 5 times/second
            except Exception as e:
                print("Error sending depth update: %s", e)
                break
    
    async def send_ticker_updates(self, websocket, symbol):
        while websocket in self.clients:
            try:
                ticker = self.orderbook.get_ticker(symbol)
                update = {
                    "e": "24hrTicker",
                    "E": int(time.time() * 1000),
                    "s": symbol,
                    "p": "0.0",
                    "P": "0.0",
                    "w": str(ticker.get('price', 0)),
                    "x": str(ticker.get('price', 0)),
                    "c": str(ticker.get('price', 0)),
                    "Q": "0.0",
                    "b": str(ticker.get('price', 0)),
                    "B": "0.0",
                    "a": str(ticker.get('price', 0)),
                    "A": "0.0",
                    "o": "0.0",
                    "h": "0.0",
                    "l": "0.0",
                    "v": "0.0",
                    "q": "0.0",
                    "O": 0,
                    "C": int(time.time() * 1000),
                    "F": 0,
                    "L": 0,
                    "n": 0
                }
                await websocket.send(json.dumps(update))
                await asyncio.sleep(1)  # 1 time/second
            except Exception as e:
                print(f"Error sending ticker update: {e}")
                break