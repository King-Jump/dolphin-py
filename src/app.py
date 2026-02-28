import asyncio
import threading
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Define allowed symbols
ALLOWED_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'JPMUSDT']

from src.api.routes import app
from src.ws.handlers.handlers import WebSocketHandler
import websockets

# Set allowed symbols in the app config
app.config['ALLOWED_SYMBOLS'] = ALLOWED_SYMBOLS

async def start_websocket_server():
    handler = WebSocketHandler(ALLOWED_SYMBOLS)
    async with websockets.serve(handler.handle_connection, "0.0.0.0", 8765):
        print("WebSocket server started on port 8765")
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