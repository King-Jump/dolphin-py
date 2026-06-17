import asyncio
import json
import time
import logging

logger = logging.getLogger(__name__)

from src.engine.matching.matching import global_spot_engine, global_futures_engine

class WebSocketHandler:
    def __init__(self, symbols):
        self.symbols = symbols
        # support small size of web sockets
        self.client_max_size = 4
        self.clients = []
        self.spot_subscriptions = {}
        self.future_subscriptions = {}
        self.depth_update_size = 30

        # update interval in seconds
        self.update_interval = 0.5

        # Start update tasks
        asyncio.create_task(self.send_future_depth_updates())
        asyncio.create_task(self.send_future_trade_updates())

        asyncio.create_task(self.send_spot_depth_updates())
        asyncio.create_task(self.send_spot_trade_updates())
    
    async def handle_connection(self, websocket, path):
        if len(self.clients) >= self.client_max_size:
            ws, _ = self.clients.pop(0)
            try:
                ws.close()
            except:
                pass

            if ws in self.spot_subscriptions:
                del self.spot_subscriptions[ws]
            if ws in self.future_subscriptions:
                del self.future_subscriptions[ws]

        self.clients.append((websocket, time.time()))

        try:
            # Parse subscription request
            async for message in websocket:
                data = json.loads(message)
                if data.get('method') == 'SUBSCRIBE':
                    params = data.get('params', [])
                    await self.handle_subscription(websocket, params, path)
        except Exception as e:
            logger.debug(f"WebSocket error: {e}")
        finally:
            for i, (ws, _) in enumerate(self.clients):
                if ws == websocket:
                    self.clients.pop(i)
                    break
            if websocket in self.spot_subscriptions:
                del self.spot_subscriptions[websocket]
    
    async def handle_subscription(self, websocket, params, path):
        for param in params:
            if 'depth' in param:
                symbol = param.split('@')[0]
                if symbol not in self.symbols:
                    continue

                if path == '/spot':
                    if websocket not in self.spot_subscriptions:
                        self.spot_subscriptions[websocket] = {'depth': set[str](), 'trade': set[str]()}
                    self.spot_subscriptions[websocket]['depth'].add(symbol)
                elif path == '/future':
                    if websocket not in self.future_subscriptions:
                        self.future_subscriptions[websocket] = {'depth': set[str](), 'trade': set[str]()}
                    self.future_subscriptions[websocket]['depth'].add(symbol)
            elif 'trade' in param:
                symbol = param.split('@')[0]
                if symbol not in self.symbols:
                    continue
                if path == '/spot':
                    if websocket not in self.spot_subscriptions:
                        self.spot_subscriptions[websocket] = {'depth': set[str](), 'trade': set[str]()}
                    self.spot_subscriptions[websocket]['trade'].add(symbol)
                elif path == '/future':
                    if websocket not in self.future_subscriptions:
                        self.future_subscriptions[websocket] = {'depth': set[str](), 'trade': set[str]()}
                    self.future_subscriptions[websocket]['trade'].add(symbol)
    
    async def send_spot_depth_updates(self):
        interval = self.update_interval
        while 1:
            cached_order_book = {}
            for websocket in self.spot_subscriptions:
                for symbol in self.spot_subscriptions[websocket]['depth']:
                    try:
                        if symbol not in cached_order_book:
                            depth = global_spot_engine.get_order_book_data(symbol, self.depth_update_size)
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
                        logger.debug("Error sending depth update: %s", e)
    
            await asyncio.sleep(interval)

    async def send_spot_trade_updates(self):
        last_trade_update_ts = 0
        interval = self.update_interval
        while 1:
            cached_trade = {}
            for websocket in self.spot_subscriptions:
                for symbol in self.spot_subscriptions[websocket]['trade']:
                    try:
                        if symbol not in cached_trade:
                            trades = global_spot_engine.get_trades(symbol)
                            updates = [{
                                "e": "trade",
                                "E": int(time.time() * 1000), # event timestamp
                                "id": trade.trade_id,
                                "s": symbol,     # symbol
                                "p": str(trade.price),         # price
                                "q": str(trade.quantity),      # quantity
                                "C": trade.timestamp,          # trade timestamp
                            } for trade in trades if trade.timestamp > last_trade_update_ts]
                            cached_trade[symbol] = updates

                            if trades and trades[-1].timestamp > last_trade_update_ts:
                                last_trade_update_ts = trades[-1].timestamp

                        updates = cached_trade[symbol]
                        for update in updates:
                            await websocket.send(json.dumps(update))
                    except Exception as e:
                        logger.debug(f"Error sending ticker update: {e}")
            await asyncio.sleep(interval)

    async def send_future_depth_updates(self):
        interval = self.update_interval
        while 1:
            cached_order_book = {}
            for websocket in self.future_subscriptions:
                for symbol in self.future_subscriptions[websocket]['depth']:
                    try:
                        if symbol not in cached_order_book:
                            depth = global_futures_engine.get_order_book_data(symbol, self.depth_update_size)
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
                        logger.debug("Error sending depth update: %s", e)
    
            await asyncio.sleep(interval)
        
    async def send_future_trade_updates(self):
        last_trade_update_ts = 0
        interval = self.update_interval
        while 1:
            cached_trade = {}
            for websocket in self.future_subscriptions:
                for symbol in self.future_subscriptions[websocket]['trade']:
                    try:
                        if symbol not in cached_trade:
                            trades = global_futures_engine.get_trades(symbol)
                            updates = [{
                                "e": "trade",
                                "E": int(time.time() * 1000), # event timestamp
                                "id": trade.trade_id,
                                "s": symbol,     # symbol
                                "p": str(trade.price),         # price
                                "q": str(trade.quantity),      # quantity
                                "C": trade.timestamp,          # trade timestamp
                            } for trade in trades if trade.timestamp > last_trade_update_ts]
                            cached_trade[symbol] = updates

                            if trades and trades[-1].timestamp > last_trade_update_ts:
                                last_trade_update_ts = trades[-1].timestamp

                        updates = cached_trade[symbol]
                        for update in updates:
                            await websocket.send(json.dumps(update))
                    except Exception as e:
                        logger.debug(f"Error sending ticker update: {e}")
            await asyncio.sleep(interval)
