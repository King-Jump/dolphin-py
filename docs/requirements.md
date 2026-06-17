# Digital Currency Exchange Project Requirements Document

## 1. Project Overview
This project aims to develop a minimalist digital currency exchange that supports both futures and spot trading, providing trading functions and market data through RESTful API and WebSocket.

## 2. Functional Requirements

### 2.1 Trading Functions
- **Spot Trading**: Support limit and market orders for spot trading
- **Futures Trading**: Support limit and market orders for futures trading
- **Order Matching**: Implement correct order matching logic, including price priority and time priority principles
- **Batch Orders**: Support batch order placement operations through RESTful API
- **Order Placement with Price Range**: Support order placement operations with price range (setting multiple orders at different price levels) through RESTful API

### 2.2 Market Data
- **Depth Data**: Provide 30 levels of order book data through WebSocket
- **Ticker Data**: Provide latest trade price and quantity through WebSocket

### 2.3 Security Control
- **Private Interfaces**: RESTful API private interfaces are only open to local access
- **Public Interfaces**: RESTful API and WebSocket public interfaces are open to the public network

## 3. Non-Functional Requirements

### 3.1 Performance Requirements
- **Low Latency**: Trading engine processing latency is less than 1ms
- **High Throughput**: Can process 10,000+ orders per second
- **High Availability**: System availability reaches 99.9%

### 3.2 Technical Requirements
- **Language Selection**: Choose high-performance development language
- **Architecture Design**: Adopt microservices architecture to ensure system scalability
- **Data Storage**: Choose high-performance storage solution

## 4. Interface Requirements

### 4.1 RESTful API

#### 4.1.1 Public Interfaces
- **GET /api/v1/market/ticker**: Get latest market trade price and quantity
- **GET /api/v1/market/depth**: Get order book data

#### 4.1.2 Private Interfaces (Local Access Only)
- **POST /api/v1/order/batch**: Batch order placement
- **POST /api/v1/order/place**: Order placement with price range
- **GET /api/v1/order/list**: Get order list
- **POST /api/v1/order/cancel**: Cancel orders

### 4.2 WebSocket Interface
- **/ws/market**: Subscribe to market data
- **depth**: 30 levels of order book data
- **ticker**: Latest trade price and quantity

## 5. Data Models

### 5.1 Order Model
- **order_id**: Order ID
- **symbol**: Trading pair
- **side**: Order side (buy/sell)
- **type**: Order type (limit/market)
- **price**: Price
- **quantity**: Quantity
- **status**: Order status (pending/filled/canceled)
- **timestamp**: Creation time

### 5.2 Trade Model
- **trade_id**: Trade ID
- **symbol**: Trading pair
- **price**: Trade price
- **quantity**: Trade quantity
- **buy_order_id**: Buyer order ID
- **sell_order_id**: Seller order ID
- **timestamp**: Trade time

## 6. System Architecture

### 6.1 Core Components
- **Trading Engine**: Handles order matching and trades
- **API Service**: Provides RESTful API interfaces
- **WebSocket Service**: Provides real-time market data
- **Data Storage**: Stores orders and trade data

### 6.2 Technology Selection
- **Development Language**: Golang (high performance, strong concurrency processing capability)
- **Web Framework**: Gin (lightweight, high performance)
- **WebSocket**: gorilla/websocket
- **Data Storage**: Redis (high-performance in-memory database)
- **Message Queue**: NATS (low-latency message passing)

## 7. Security Requirements
- **Interface Access Control**: Private interfaces only allow local access
- **Data Transmission Encryption**: Use HTTPS and WSS protocols
- **Prevention of Malicious Requests**: Implement request rate limiting

## 8. Testing Requirements
- **Functional Testing**: Test trading functions and API interfaces
- **Performance Testing**: Test system throughput and latency
- **Security Testing**: Test interface access control

## 9. Deployment Requirements
- **Containerization**: Deploy using Docker containers
- **Orchestration**: Use Docker Compose to manage containers
- **Monitoring**: Integrate Prometheus and Grafana monitoring system

## 10. Project Milestones
1. Complete requirements document and design document
2. Implement core trading engine functionality
3. Implement RESTful API interfaces
4. Implement WebSocket interfaces
5. Conduct system testing and performance optimization
6. Deployment and launch