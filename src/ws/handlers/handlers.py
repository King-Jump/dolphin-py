import asyncio
import json
import time
from src.engine.matching.matching import global_engine

class WebSocketHandler:
    def __init__(self, symbols):
        self.symbols = symbols
        # support small size of web sockets
        self.client_max_size = 3
        self.clients = []
        self.subscriptions = {}
        self.depth_update_size = 30

        # Start update tasks
        asyncio.create_task(self.send_depth_updates())
        asyncio.create_task(self.send_trade_updates())
    
    async def handle_connection(self, websocket, path):
        if len(self.clients) >= self.client_max_size:
            ws, _ = self.clients.pop(0)
            try:
                ws.close()
            except:
                pass

            if ws in self.subscriptions:
                del self.subscriptions[ws]

        self.clients.append((websocket, time.time()))

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
            for i, (ws, _) in enumerate(self.clients):
                if ws == websocket:
                    self.clients.pop(i)
                    break
            if websocket in self.subscriptions:
                del self.subscriptions[websocket]
    
    async def handle_subscription(self, websocket, params):
        for param in params:
            if 'depth' in param:
                symbol = param.split('@')[0]
                if symbol not in self.symbols:
                    continue
                if websocket not in self.subscriptions:
                    self.subscriptions[websocket] = {'depth': set[str](), 'trade': set[str]()}
                self.subscriptions[websocket]['depth'].add(symbol)
            elif 'aggTrade' in param:
                symbol = param.split('@')[0]
                if symbol not in self.symbols:
                    continue
                if websocket not in self.subscriptions:
                    self.subscriptions[websocket] = {'depth': set[str](), 'trade': set[str]()}
                self.subscriptions[websocket]['trade'].add(symbol)
    
    async def send_depth_updates(self):
        while 1:
            cached_order_book = {}
            for websocket, _ in self.clients:
                if websocket in self.subscriptions:
                    for symbol in self.subscriptions[websocket]['depth']:
                        try:
                            if symbol not in cached_order_book:
                                depth = global_engine.get_order_book_data(symbol, self.depth_update_size)
                                update = {
                                    "e": "depthUpdate",
                                    "E": int(time.time() * 1000),
                                    "s": symbol,
                                    "b": depth.bids,
                                    "a": depth.asks
                                }
                                cached_order_book[symbol] = update
                            update = cached_order_book[symbol]
                            await websocket.send(json.dumps(update))
                        except Exception as e:
                            print(f"Error sending depth update: {e}")

            await asyncio.sleep(0.2)  # 5 times/second

    async def send_trade_updates(self):
        last_trade_update_ts = 0
        while 1:
            cached_trade = {}
            for websocket, _ in self.clients:
                if websocket in self.subscriptions:
                    for symbol in self.subscriptions[websocket]['trade']:
                        try:
                            if symbol not in cached_trade:
                                trades = global_engine.get_trades(symbol)
                                updates = [{
                                    "e": "aggTrade",
                                    "E": int(time.time() * 1000), # event timestamp
                                    "s": symbol,     # symbol
                                    "p": str(trade.price),         # price
                                    "q": str(trade.quantity),      # quantity
                                    "C": trade.timestamp,          # trade timestamp
                                } for trade in trades if trade.timestamp > last_trade_update_ts]
                                cached_trade[symbol] = updates

                            updates = cached_trade[symbol]
                            for update in updates:
                                await websocket.send(json.dumps(update))
                        except Exception as e:
                            print(f"Error sending trade update: {e}")
            last_trade_update_ts = int(time.time() * 1000)
            await asyncio.sleep(0.2)  # 5 times/second
