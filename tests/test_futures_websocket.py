import asyncio
import json
import websockets
import time

WS_URL = "ws://localhost:8765/future"

async def test_futures_websocket():
    print("Testing futures WebSocket functionality...")
    
    try:
        # Connect to WebSocket server
        async with websockets.connect(WS_URL) as websocket:
            print("WebSocket connected successfully!")
            
            # Test 1: Subscribe to depth updates for BTCUSDT
            print("\n1. Testing depth subscription...")
            subscribe_depth = {
                "method": "SUBSCRIBE",
                "params": ["BTCUSDT@depth"],
                "id": 1
            }
            await websocket.send(json.dumps(subscribe_depth))
            print("Sent depth subscription request")
            
            # Test 2: Subscribe to trade updates for BTCUSDT
            print("\n2. Testing trade subscription...")
            subscribe_trade = {
                "method": "SUBSCRIBE",
                "params": ["JPMUSDT@trade"],
                "id": 2
            }
            await websocket.send(json.dumps(subscribe_trade))
            print("Sent trade subscription request")
            
            # Test 3: Subscribe to both depth and trade for ETHUSDT
            print("\n3. Testing combined subscription...")
            subscribe_both = {
                "method": "SUBSCRIBE",
                "params": ["ETHUSDT@depth", "ETHUSDT@trade"],
                "id": 3
            }
            await websocket.send(json.dumps(subscribe_both))
            print("Sent combined subscription request")
            
            # Test 4: Receive and print messages for 10 seconds
            print("\n4. Receiving WebSocket messages...")
            start_time = time.time()
            message_count = 0
            
            while time.time() - start_time < 100:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1)
                    message_data = json.loads(message)
                    message_count += 1
                    
                    if message_data.get('e') == 'depthUpdate':
                        symbol = message_data.get('s')
                        bids = message_data.get('b', [])
                        asks = message_data.get('a', [])
                        print(f"Depth update for {symbol}:\n  bids: {bids}\n  asks: {asks}")
                    elif message_data.get('e') == 'trade':
                        symbol = message_data.get('s')
                        price = message_data.get('p')
                        quantity = message_data.get('q')
                        print(f"Trade update for {message_data.get('id')} {symbol}: {quantity} @ {price}")
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"Error receiving message: {e}")
                    break
            
            print(f"\nReceived {message_count} messages in 10 seconds")
            
            print("\nFutures WebSocket tests completed!")
            
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    asyncio.run(test_futures_websocket())
