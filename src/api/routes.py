from flask import Flask, request
from src.api.handlers.spot import SpotHandler
from src.api.handlers.futures import FuturesHandler
from src.api.middleware.auth import local_only

app = Flask(__name__)
spot_handler = SpotHandler()
futures_handler = FuturesHandler()

# Spot API routes
@app.route('/api/v3/order', methods=['POST'])
@local_only
def spot_new_order():
    return spot_handler.new_order(request.json)

@app.route('/api/v3/batchOrders', methods=['POST'])
@local_only
def spot_new_batch_order():
    return spot_handler.new_batch_order(request.json)

@app.route('/api/v3/order', methods=['DELETE'])
@local_only
def spot_cancel_order():
    return spot_handler.cancel_orders(request.args.get('symbol'),
        request.args.get('orderIds').split(','))

@app.route('/api/v3/openOrders', methods=['GET'])
@local_only
def spot_open_orders():
    return spot_handler.open_orders(request.args)

@app.route('/api/v3/mock', methods=['POST'])
@local_only
def spot_mock_trade():
    return spot_handler.mock_trade(request.json)

# Public Spot API
@app.route('/api/v3/depth', methods=['GET'])
def spot_depth():
    return spot_handler.get_depth(request.args)

@app.route('/api/v3/ticker/price', methods=['GET'])
def spot_ticker_price():
    return spot_handler.get_ticker_price(request.args)

@app.route('/api/v3/klines', methods=['GET'])
def spot_klines():
    return spot_handler.get_klines(request.args)

@app.route('/api/v3/trades', methods=['GET'])
def spot_trades():
    return spot_handler.get_trades(request.args)



# Futures API routes
@app.route('/fapi/v1/order', methods=['POST'])
@local_only
def futures_new_order():
    return futures_handler.new_order(request.json)

@app.route('/fapi/v1/batchOrders', methods=['POST'])
@local_only
def futures_new_batch_order():
    return futures_handler.new_batch_order(request.json)

@app.route('/fapi/v1/order', methods=['DELETE'])
@local_only
def futures_cancel_orders():
    return futures_handler.cancel_orders(request.args.get('symbol'),
        request.args.get('orderIds').split(','))

@app.route('/fapi/v1/openOrders', methods=['GET'])
@local_only
def futures_open_orders():
    return futures_handler.open_orders(request.args)

@app.route('/fapi/v3/mock', methods=['POST'])
@local_only
def futures_mock_trade():
    return futures_handler.mock_trade(request.json)

# Public Futures API
@app.route('/fapi/v1/depth', methods=['GET'])
def futures_depth():
    return futures_handler.get_depth(request.args)

@app.route('/fapi/v1/ticker/price', methods=['GET'])
def futures_ticker_price():
    return futures_handler.get_ticker_price(request.args)

@app.route('/fapi/v1/klines', methods=['GET'])
def futures_klines():
    return futures_handler.get_klines(request.args)

@app.route('/fapi/v1/trades', methods=['GET'])
def futures_trades():
    return futures_handler.get_trades(request.args)
