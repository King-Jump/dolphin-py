# Digital Currency Exchange System Design Document

## 1. System Architecture

### 1.1 Overall Architecture
The system adopts a microservices architecture, consisting of the following core components:

1. **Trading Engine**: Responsible for order matching and trade processing
2. **API Service**: Provides RESTful API interfaces
3. **WebSocket Service**: Provides real-time market data
4. **Data Storage**: Stores orders and trade data
5. **Message Queue**: For message passing between components

### 1.2 Component Relationships
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  API Service│────>│ Trading Engine │────>│  Data Storage │
└─────────────┘     └─────────────┘     └─────────────┘
       ↑                  │                  │
       │                  ↓                  │
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│WebSocket Service│<────│ Message Queue │<────│             │
└─────────────┘     └─────────────┘     └─────────────┘
```

### 1.3 Technology Selection
| Component | Technology | Version | Selection Reason |
|-----------|------------|---------|------------------|
| Development Language | Python | 3.9+ | High development efficiency, rich ecosystem, suitable for rapid trading system development |
| Web Framework | Flask | 2.0.1+ | Lightweight, flexible, suitable for building RESTful APIs |
| WebSocket | websockets | 10.1+ | Native support for asyncio, excellent performance |
| Data Storage | In-memory Storage | - | Trading engine uses in-memory storage to improve matching speed |
| Data Storage (Optional) | Redis | 6.0+ | High-performance in-memory database, suitable for storing order book and trade data |

## 2. Data Model Design

### 2.1 Order Model
| Field Name | Type | Description |
|------------|------|-------------|
| order_id | string | Order ID, UUID format |
| symbol | string | Trading pair, e.g., BTC/USDT |
| side | string | Order side, buy/sell |
| type | string | Order type, limit/market |
| price | float64 | Order price |
| quantity | float64 | Order quantity |
| filled_quantity | float64 | Filled quantity |
| status | string | Order status, pending/filled/canceled |
| timestamp | int64 | Creation timestamp, milliseconds |
| update_timestamp | int64 | Update timestamp, milliseconds |

### 2.2 Trade Model
| Field Name | Type | Description |
|------------|------|-------------|
| trade_id | string | Trade ID, UUID format |
| symbol | string | Trading pair, e.g., BTC/USDT |
| price | float64 | Trade price |
| quantity | float64 | Trade quantity |
| buy_order_id | string | Buyer order ID |
| sell_order_id | string | Seller order ID |
| timestamp | int64 | Trade timestamp, milliseconds |

### 2.3 Order Book Model
| Field Name | Type | Description |
|------------|------|-------------|
| symbol | string | Trading pair |
| bids | []OrderLevel | Buy price levels |
| asks | []OrderLevel | Sell price levels |
| timestamp | int64 | Update timestamp, milliseconds |

### 2.4 OrderLevel Model
| Field Name | Type | Description |
|------------|------|-------------|
| price | float64 | Price |
| quantity | float64 | Quantity |

### 2.5 Ticker Model
| Field Name | Type | Description |
|------------|------|-------------|
| symbol | string | Trading pair |
| price | float64 | Latest trade price |
| quantity | float64 | Latest trade quantity |
| timestamp | int64 | Update timestamp, milliseconds |

## 3. Core Function Design

### 3.1 Trading Engine

#### 3.1.1 Order Matching Algorithm
- **Price Priority**: Higher price buy orders take priority over lower price buy orders, lower price sell orders take priority over higher price sell orders
- **Time Priority**: Orders with the same price are matched in the order they are submitted

#### 3.1.2 Matching Process
1. Receive new order
2. Match according to order type (limit/market) and direction (buy/sell)
3. Generate trade records
4. Update order status and order book
5. Send trade and order book update notifications

#### 3.1.3 Spot and Futures Trading Differences
- **Spot Trading**: Directly match buy and sell orders, transfer assets after execution
- **Futures Trading**: Match buy and sell orders, record positions and profit/loss after execution

### 3.2 API Service

#### 3.2.1 Public Endpoints

##### Spot Endpoints
- **GET /api/v3/ticker/price**: Get latest spot market trade price
- **GET /api/v3/depth**: Get spot order book data, support specifying trading pair and depth
- **GET /api/v3/klines**: Get spot kline data, support specifying trading pair, time interval and quantity limit

##### Futures Endpoints
- **GET /fapi/v1/ticker/price**: Get latest futures market trade price
- **GET /fapi/v1/depth**: Get futures order book data, support specifying trading pair and depth
- **GET /fapi/v1/klines**: Get futures kline data, support specifying trading pair, time interval and quantity limit

#### 3.2.2 Private Endpoints (Local Access Only)

##### Spot Endpoints
- **POST /api/v3/order**: Spot order placement
- **POST /api/v3/batchOrders**: Spot batch order placement
- **GET /api/v3/openOrders**: Get spot open orders
- **GET /api/v3/allOrders**: Get all spot orders
- **POST /api/v3/order/cancel**: Cancel spot order
- **POST /api/v3/order/cancelAll**: Cancel all spot orders

##### Futures Endpoints
- **POST /fapi/v1/order**: Futures order placement
- **POST /fapi/v1/batchOrders**: Futures batch order placement
- **GET /fapi/v1/openOrders**: Get futures open orders
- **GET /fapi/v1/allOrders**: Get all futures orders
- **POST /fapi/v1/order/cancel**: Cancel futures order
- **POST /fapi/v1/order/cancelAll**: Cancel all futures orders

### 3.3 WebSocket Service

#### 3.3.1 Subscription Mechanism
- Clients subscribe to market data via WebSocket connection
- Support subscribing to depth and ticker data for specific trading pairs
- Support unsubscribing

#### 3.3.2 Data Push
- **depth**: 30 levels of order book data, pushed when the order book changes
- **ticker**: Latest trade price and quantity, pushed when there is a new trade

## 4. System Flow Design

### 4.1 Order Placement Flow
1. Client sends order request to API service
2. API service validates request parameters
3. API service sends order to trading engine
4. Trading engine processes order and performs matching
5. Trading engine updates order status and order book
6. WebSocket service directly gets data from trading engine and pushes to clients

### 4.2 Batch Order Placement Flow
1. Client sends batch order request to API service
2. API service validates request parameters
3. API service sends multiple orders in batch to trading engine
4. Trading engine processes orders one by one and performs matching
5. Trading engine updates order status and order book
6. WebSocket service directly gets data from trading engine and pushes to clients

### 4.3 Order Placement with Price Range Flow
1. Client sends order placement request with price range, price step and order quantity to API service
2. API service validates request parameters and generates multiple orders
3. API service sends generated orders in batch to trading engine
4. Trading engine processes orders one by one and performs matching
5. Trading engine updates order status and order book
6. WebSocket service directly gets data from trading engine and pushes to clients

## 5. Security Design

### 5.1 Interface Access Control
- **Private Endpoints**: Restricted by IP whitelist, only allowing local access (127.0.0.1)
- **Public Endpoints**: No IP restrictions, allowing public access

### 5.2 Data Transmission Encryption
- Use HTTPS protocol for RESTful API data transmission
- Use WSS protocol for WebSocket data transmission

### 5.3 Prevention of Malicious Requests
- Implement request rate limiting to prevent API abuse
- Strictly validate request parameters to prevent injection attacks

## 6. Performance Optimization

### 6.1 Trading Engine Optimization
- Use in-memory order book to improve matching speed
- Use concurrent processing to improve throughput
- Optimize matching algorithm to reduce computational complexity

### 6.2 API Service Optimization
- Use Flask framework's routing and middleware
- Implement request caching to reduce redundant calculations
- Use connection pooling to reduce database connection overhead

### 6.3 WebSocket Service Optimization
- Use asyncio to handle WebSocket connections, improving concurrency capability
- Implement batch message pushing to reduce network transmission times
- Use compression algorithm to reduce data transmission volume

## 7. Deployment Design

### 7.1 Containerized Deployment
- Use Docker containers to package each service
- Use Docker Compose to manage container orchestration

### 7.2 Service Configuration
| Service | Configuration Item | Description |
|---------|-------------------|-------------|
| API Service | PORT | Service port |
| WebSocket Service | PORT | Service port |
| Redis (Optional) | REDIS_URL | Redis connection address |



## 8. Testing Design

### 8.1 Functional Testing
- Test order submission and matching functionality
- Test batch order placement and order placement with price range
- Test WebSocket data pushing
- Test API interface responses

### 8.2 Performance Testing
- Test trading engine throughput and latency
- Test API service concurrent processing capability
- Test WebSocket service message pushing performance

### 8.3 Security Testing
- Test private interface access control
- Test data transmission encryption
- Test system defense against malicious requests

## 9. Code Structure

### 9.1 Directory Structure
```
├── exchange/             # Project root directory
│   ├── src/              # Source code
│   │   ├── engine/       # Trading engine
│   │   │   ├── matching/ # Order matching algorithm
│   │   │   ├── orderbook/ # Order book management
│   │   │   └── types/    # Data type definitions
│   │   ├── api/          # API service
│   │   │   ├── handlers/ # Request handlers
│   │   │   ├── middleware/ # Middleware
│   │   │   └── routes.py # Route definitions
│   │   ├── ws/           # WebSocket service
│   │   │   └── handlers.py # Connection handlers
│   │   └── common/       # Common components
│   │       ├── config/   # Configuration management
│   │       ├── utils/    # Utility functions
│   │       └── models/   # Data models
│   ├── tests/            # Test code
│   ├── configs/          # Configuration files
│   ├── docs/             # Documentation
│   ├── api.py            # API service entry
│   ├── ws.py             # WebSocket service entry
│   └── requirements.txt  # Dependencies
└── README.md             # Project description
```

### 9.2 Core Modules
- **Trading Engine**: Handles order matching and trades
- **Order Book**: Maintains price levels for buy and sell orders
- **API Service**: Handles HTTP requests and responses
- **WebSocket Service**: Handles real-time data pushing
- **Message Queue**: Implements message passing between components

## 10. Project Milestones

1. **Complete Requirements and Design Documents**: Clarify system functionality and architecture
2. **Implement Trading Engine Core**: Complete order matching and trade logic
3. **Implement API Service**: Complete RESTful API interfaces
4. **Implement WebSocket Service**: Complete real-time data pushing
5. **Conduct System Testing**: Test functionality and performance
6. **Deployment and Launch**: Containerized deployment and monitoring