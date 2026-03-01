import asyncio
import threading
import sys
import os
import logging
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)

# Configure logging
log_file = os.path.join(log_dir, 'app.log')
handler = RotatingFileHandler(log_file, maxBytes=1073741824, backupCount=1)  # 1GB limit
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
handler.setLevel(logging.DEBUG)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(handler)

logger = logging.getLogger(__name__)

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Define allowed symbols
ALLOWED_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'JPMUSDT']

from src.api.routes import app
from src.ws.handlers.handlers import WebSocketHandler
import websockets

# Set allowed symbols in the app config
app.config['ALLOWED_SYMBOLS'] = ALLOWED_SYMBOLS

async def handle_websocket(websocket, path):
    if path == '/spot':
        handler = WebSocketHandler(ALLOWED_SYMBOLS)
        await handler.handle_connection(websocket, path)
    elif path == '/future':
        handler = WebSocketHandler(ALLOWED_SYMBOLS)
        await handler.handle_connection(websocket, path)
    else:
        await websocket.close()

async def start_websocket_server():
    async with websockets.serve(handle_websocket, "0.0.0.0", 8765):
        logger.debug("WebSocket server started on port 8765")
        await asyncio.Future()  # Run indefinitely

def start_flask():
    app.run(host="0.0.0.0", port=8763, debug=False)

if __name__ == "__main__":
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Start WebSocket server
    asyncio.run(start_websocket_server())
