from flask import jsonify
from src.engine.matching.matching import MatchingEngine
from src.engine.orderbook.orderbook import OrderBook

class FuturesHandler:
    def __init__(self):
        self.engine = MatchingEngine()
        self.orderbook = OrderBook()
    
    def new_order(self, data):
        try:
            trades, order = self.engine.create_order(
                symbol=data.get('symbol'),
                side=data.get('side'),
                type=data.get('type'),
                quantity=float(data.get('quantity')),
                price=float(data.get('price')) if data.get('price') else None,
                is_futures=True
            )
            if order:
                return jsonify({
                    "code": 200,
                    "data": {
                        "symbol": order.symbol,
                        "orderId": order.order_id,
                        "clientOrderId": order.client_order_id,
                        "transactTime": order.timestamp,
                        "price": order.price,
                        "origQty": order.quantity,
                        "executedQty": order.executed_quantity,
                        "status": order.status,
                        "type": order.type,
                        "side": order.side
                    }
                })
            return jsonify({"code": 400, "msg": "Failed to create order"}), 400
        except Exception as e:
            return jsonify({"code": 500, "msg": str(e)}), 500
    
    def new_batch_order(self, data):
        try:
            orders = data.get('batchOrders', [])
            results = []
            for order_data in orders:
                trades, order = self.engine.create_order(
                    symbol=order_data.get('symbol'),
                    side=order_data.get('side'),
                    type=order_data.get('type'),
                    quantity=float(order_data.get('quantity')),
                    price=float(order_data.get('price')) if order_data.get('price') else None,
                    is_futures=True
                )
                if order:
                    results.append({
                        "symbol": order.symbol,
                        "orderId": order.order_id,
                        "clientOrderId": order.client_order_id,
                        "transactTime": order.timestamp,
                        "price": order.price,
                        "origQty": order.quantity,
                        "executedQty": order.executed_quantity,
                        "status": order.status,
                        "type": order.type,
                        "side": order.side
                    })
            return jsonify({
                "code": 200,
                "data": results
            })
        except Exception as e:
            return jsonify({"code": 500, "msg": str(e)}), 500
    
    def cancel_orders(self, symbol, order_ids):
        try:
            results = []
            for order_id in order_ids:
                cancelled = self.engine.cancel_order(symbol, order_id)
                if cancelled:
                    results.append({
                        "symbol": cancelled.symbol,
                        "orderId": cancelled.order_id,
                        "clientOrderId": cancelled.client_order_id,
                        "transactTime": cancelled.timestamp,
                        "price": cancelled.price,
                        "origQty": cancelled.quantity,
                        "executedQty": cancelled.executed_quantity,
                        "status": "CANCELED",
                        "type": cancelled.type,
                        "side": cancelled.side
                    })
            return jsonify({
                "code": 200,
                "data": results
            })
        except Exception as e:
            return jsonify({"code": 500, "msg": str(e)}), 500
    
    def open_orders(self, args):
        symbol = args.get('symbol')
        orders = self.engine.get_open_orders(symbol, is_futures=True)
        return jsonify({
            "code": 200,
            "data": [
                {
                    "symbol": order.symbol,
                    "orderId": order.order_id,
                    "clientOrderId": order.client_order_id,
                    "price": order.price,
                    "origQty": order.quantity,
                    "executedQty": order.executed_quantity,
                    "status": order.status,
                    "type": order.type,
                    "side": order.side
                }
                for order in orders
            ]
        })
    
    def mock_trade(self, args):
        symbol = args.get('symbol')
        side = args.get('side')
        price = args.get('price')
        quantity = args.get('quantity')
        return jsonify({
            "code": 200,
            "data": {
                "symbol": symbol,
                "price": price,
                "quantity": quantity,
                "status": "FAILED"
            }
        })
    
    def get_depth(self, args):
        symbol = args.get('symbol', 'BTCUSDT')
        limit = int(args.get('limit', 30))
        depth = self.orderbook.get_depth(symbol, limit)
        return jsonify({
            "code": 200,
            "data": {
                "lastUpdateId": depth.get('lastUpdateId', 0),
                "bids": depth.get('bids', []),
                "asks": depth.get('asks', [])
            }
        })
    
    def get_ticker_price(self, args):
        symbol = args.get('symbol', 'BTCUSDT')
        ticker = self.orderbook.get_ticker(symbol)
        return jsonify({
            "code": 200,
            "data": {
                "symbol": symbol,
                "price": str(ticker.get('price', 0)),
                "quantity": "10.00"
            }
        })
    
    def get_klines(self, args):
        symbol = args.get('symbol', 'BTCUSDT')
        interval = args.get('interval', '1m')
        # Mock kline data
        return jsonify({
            "code": 200,
            "data": [
                {
                    "ot": 1617295200000,  # Open time
                    "o": "58950.00",     # Open price
                    "h": "59200.00",     # High price
                    "l": "58800.00",     # Low price
                    "c": "59100.00",     # Close price
                    "v": "10.5",         # Volume
                    "ct": 1617295799999,   # Close time
                    "a": "619575.00"     # Quote asset volume
                }
            ]
        })
