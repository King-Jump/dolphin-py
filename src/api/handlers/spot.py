import logging
from flask import jsonify, current_app
import time
from src.engine.matching.matching import global_spot_engine
from src.engine.funding.funding import SPOT_FUNDING
import traceback

logger = logging.getLogger(__name__)

# Map interval to milliseconds
interval_map = {
    '1m': 60 * 1000,
    '1h': 60 * 60 * 1000,
    '1d': 24 * 60 * 60 * 1000,
}

class SpotHandler:
    def _validate_symbol(self, symbol):
        """Validate if symbol is allowed"""
        allowed_symbols = current_app.config.get('ALLOWED_SYMBOLS', ['BTCUSDT'])
        return symbol in allowed_symbols

    def new_order(self, data):
        """ Process new order, first check if it can be matched, add to order book if not fully filled """
        try:
            logger.debug(f"New order data: {data}")
            symbol = data.get('symbol')
            if not self._validate_symbol(symbol):
                return jsonify({"code": 400, "msg": f"Symbol {symbol} is not allowed"}), 400
            if not data.get('uid'):
                return jsonify({"code": 400, "msg": "uid is required"}), 400

            logger.debug(f"Calling create_order with order_type={data.get('type')}, client_order_id={data.get('client_order_id')}")
            # trades, order = global_spot_engine.create_order(
            result, order = SPOT_FUNDING.put_spot_order(
                uid=data['uid'],
                symbol=symbol,
                side=data.get('side'),
                order_type=data.get('type'),
                time_in_force=data.get('time_in_force'),
                quantity=float(data.get('quantity')),
                price=float(data.get('price')) if data.get('price') else 0,
                client_order_id=data.get('client_order_id')
            )
            if result:
                return jsonify({
                    "code": 200,
                    "data": {
                        "uid": order.uid,
                        "symbol": order.symbol,
                        "orderId": order.order_id,
                        "clientOrderId": order.client_order_id,
                        "type": order.type,
                        "timeInForce": order.time_in_force,
                        "transactTime": order.timestamp,
                        "price": order.price,
                        "origQty": order.quantity,
                        "executedQty": order.filled_quantity,
                        "status": order.status,
                        "type": order.type,
                        "side": order.side
                    }
                })
            return jsonify({"code": 400, "msg": str(order)}), 400
        except Exception as e:
            import traceback
            logger.debug(f"Error in new_order: {e}")
            traceback.print_exc()
            return jsonify({"code": 500, "msg": str(e)}), 500

    def new_batch_order(self, data):
        try:
            if not data.get('uid'):
                return jsonify({"code": 400, "msg": "uid is required"}), 400

            params = data.get('batchOrders', [])
            #_, orders = global_spot_engine.create_orders(
            result, orders = SPOT_FUNDING.put_spot_orders(
                uid=data['uid'],
                params=params
            )
            if result:
                return jsonify({
                    "code": 200,
                    "data": [{
                        "symbol": order.symbol,
                        "orderId": order.order_id,
                        "clientOrderId": order.client_order_id,
                        "timeInForce": order.time_in_force,
                        "transactTime": order.timestamp,
                        "price": order.price,
                        "origQty": order.quantity,
                        "executedQty": order.filled_quantity,
                        "status": order.status,
                        "type": order.type,
                        "side": order.side
                    } for order in orders]
                })
            return jsonify({"code": 400, "msg": str(orders)}), 400
        except Exception as e:
            traceback.print_exc()
            return jsonify({"code": 500, "msg": str(e)}), 500

    def cancel_orders(self, uid, symbol, order_ids):
        try:
            if not uid:
                return jsonify({"code": 400, "msg": "uid is required"}), 400

            if not self._validate_symbol(symbol):
                return jsonify({"code": 400, "msg": f"Symbol {symbol} is not allowed"}), 400

            # results = global_spot_engine.cancel_orders(
            result, orders = SPOT_FUNDING.cancel_spot_orders(
                uid=uid,
                symbol=symbol,
                order_ids=order_ids
            )
            if result:
                return jsonify({
                    "code": 200,
                    "data": [{
                        "uid": cancelled.uid,
                        "symbol": cancelled.symbol,
                        "orderId": cancelled.order_id,
                        "status": cancelled.status,
                    } for cancelled in orders]
                })
            return jsonify({"code": 400, "msg": str(orders)}), 400
        except Exception as e:
            return jsonify({"code": 500, "msg": str(e)}), 500

    def open_orders(self, args):
        symbol = args.get('symbol')
        logger.debug(f"open_orders symbol: {symbol}")
        if symbol and not self._validate_symbol(symbol):
            return jsonify({"code": 400, "msg": f"Symbol {symbol} is not allowed"}), 400

        if not args.get('uid'):
            return jsonify({"code": 400, "msg": "uid is required"}), 400

        orders = global_spot_engine.get_open_orders(uid=args['uid'], symbol=symbol)
        logger.debug(f"MONITOR: uid={args['uid']} symbol={symbol} open_orders: {len(orders)}")
        return jsonify({
            "code": 200,
            "data": [
                {
                    "uid": order.uid,
                    "symbol": order.symbol,
                    "orderId": order.order_id,
                    "clientOrderId": order.client_order_id,
                    "timeInForce": order.time_in_force,
                    "transactTime": order.timestamp,
                    "price": order.price,
                    "origQty": order.quantity,
                    "executedQty": order.filled_quantity,
                    "status": order.status,
                    "type": order.type,
                    "side": order.side
                }
                for order in orders
            ]
        })

    def mock_trade(self, args):
        symbol = args.get('symbol')
        if not self._validate_symbol(symbol):
            return jsonify({"code": 400, "msg": f"Symbol {symbol} is not allowed"}), 400

        if not args.get('uid'):
            return jsonify({"code": 400, "msg": "uid is required"}), 400
        
        side = args.get('side')
        price = args.get('price')
        quantity = args.get('quantity')
        if not side or not price or not quantity:
            return jsonify({'code': 500, 'data': "invalid parameter"})

        global_spot_engine.append_trade(uid=args['uid'], symbol=symbol, price=float(price), quantity=float(quantity))
        global_spot_engine.update_klines(symbol, float(price), float(quantity))
        return jsonify({
            "code": 200,
            "data": {
                "uid": args['uid'],
                "symbol": symbol,
                'side': side,
                "price": price,
                "quantity": quantity,
                "status": "FILLED"
            }
        })

    def get_depth(self, args):
        symbol = args.get('symbol', 'BTCUSDT')
        if not self._validate_symbol(symbol):
            return jsonify({"code": 400, "msg": f"Symbol {symbol} is not allowed"}), 400
        
        limit = int(args.get('limit', 30))
        depth = global_spot_engine.get_order_book(symbol).get_order_book(limit)
        return jsonify({
            "code": 200,
            "data": {
                "lastUpdateId": int(time.time() * 1000),
                "bids": depth.bids,
                "asks": depth.asks
            }
        })

    def get_ticker_price(self, args):
        symbol = args.get('symbol', 'BTCUSDT')
        if not self._validate_symbol(symbol):
            return jsonify({"code": 400, "msg": f"Symbol {symbol} is not allowed"}), 400

        ticker = global_spot_engine.get_trades(symbol, 1)
        if ticker:
            ticker = ticker[0]
        else:
            return jsonify({"code": 400, "msg": f"Symbol {symbol} is not traded"}), 400
        return jsonify({
            "code": 200,
            "data": {
                "symbol": symbol,
                "price": str(ticker.price),
                "quantity": str(ticker.quantity)
            }
        })

    def get_klines(self, args):
        symbol = args.get('symbol', 'BTCUSDT')
        if not self._validate_symbol(symbol):
            return jsonify({"code": 400, "msg": f"Symbol {symbol} is not allowed"}), 400

        interval = args.get('interval', '1m')
        if interval not in interval_map:
            return jsonify({"code": 400, "msg": f"Interval {interval} is not allowed"}), 400

        limit = int(args.get('limit', 50))
        kline_data = global_spot_engine.get_klines(symbol, interval, limit)

        klines = [{
                "ot": bar[0],                  # Open time
                "o": str(bar[1]),     # Open price
                "h": str(bar[2]),# High price
                "l": str(bar[3]),# Low price
                "c": str(bar[4]), # Close price
                "v": str(bar[5]),                       # Volume
                "ct": bar[6],  # Close time
                "a": str(bar[7])  # Quote asset volume 
            } for bar in kline_data]

        return jsonify({
            "code": 200,
            "data": klines
        })

    def get_trades(self, args):
        symbol = args.get('symbol', 'BTCUSDT')
        if not self._validate_symbol(symbol):
            return jsonify({"code": 400, "msg": f"Symbol {symbol} is not allowed"}), 400

        uid = args.get('uid')
        if not uid:
            return jsonify({"code": 400, "msg": "uid is required"}), 400

        limit = int(args.get('limit', 50))
        trades = global_spot_engine.get_trades(uid, symbol, limit)
        return jsonify({
            "code": 200,
            "data": [
                {
                    "uid": uid,
                    "id": trade.trade_id,
                    "price": str(trade.price),
                    "quantity": str(trade.quantity),
                    "time": trade.timestamp,
                    "isBuyerMaker": False  # True if maker is buyer
                }
                for trade in trades
            ]
        })

    def order_status(self, args):
        symbol = args.get('symbol')
        order_id = args.get('orderId')

        if not symbol:
            return jsonify({"code": 400, "msg": "Symbol is required"}), 400
        if not order_id:
            return jsonify({"code": 400, "msg": "orderId is required"}), 400

        uid = args.get('uid')
        if not uid:
            return jsonify({"code": 400, "msg": "uid is required"}), 400

        if not self._validate_symbol(symbol):
            return jsonify({"code": 400, "msg": f"Symbol {symbol} is not allowed"}), 400

        order = global_spot_engine.get_order(uid, symbol, order_id)
        if not order:
            return jsonify({"code": 404, "msg": "Order not found"}), 404

        return jsonify({
            "code": 200,
            "data": {
                "uid": uid,
                "symbol": order.symbol,
                "orderId": order.order_id,
                "clientOrderId": order.client_order_id,
                "price": order.price,
                "origQty": order.quantity,
                "executedQty": order.filled_quantity,
                "status": order.status,
                "type": order.type,
                "side": order.side
            }
        })
