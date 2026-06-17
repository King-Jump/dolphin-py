# Digital Currency Exchange Deployment Guide

## 1. Project Structure

```
├── cmd/                  # Command line entry
│   ├── engine/           # Trading engine entry
│   ├── api/              # API service entry
│   └── ws/               # WebSocket service entry
├── internal/             # Internal packages
│   ├── engine/           # Trading engine core
│   │   ├── matching/     # Order matching algorithm
│   │   ├── orderbook/    # Order book management
│   │   └── types/        # Data type definitions
│   ├── api/              # API service
│   │   ├── handlers/     # Request handlers
│   │   ├── middleware/   # Middleware
│   │   └── routes/       # Route definitions
│   ├── ws/               # WebSocket service
│   │   ├── handlers/     # Connection handlers
│   │   └── publishers/   # Data publishers
│   └── common/           # Common components
│       ├── config/       # Configuration management
│       ├── utils/        # Utility functions
│       └── models/       # Data models
├── pkg/                  # Exportable packages
├── configs/              # Configuration files
├── docker/               # Docker configuration
├── docs/                 # Documentation
├── bin/                  # Compilation output
├── go.mod                # Go module file
└── go.sum                # Dependency verification file
```

## 2. Environment Requirements

### 2.1 Hardware Requirements
- **CPU**: 8 cores or more
- **Memory**: 16GB or more
- **Network**: Gigabit network

### 2.2 Software Requirements
- **Go**: 1.20+
- **Redis**: 7.0+ (Optional, for data storage)
- **NATS**: 2.9.0+ (Optional, for message queue)
- **Docker**: 20.04+ (Optional, for containerized deployment)

## 3. Build and Run

### 3.1 Local Build

1. **Install dependencies**
   ```bash
   go mod tidy
   ```

2. **Build API service**
   ```bash
   go build -o bin/api cmd/api/main.go
   ```

3. **Build WebSocket service**
   ```bash
   go build -o bin/ws cmd/ws/main.go
   ```

4. **Run API service**
   ```bash
   ./bin/api
   ```
   API service will run on `http://localhost:8080`

5. **Run WebSocket service**
   ```bash
   ./bin/ws
   ```
   WebSocket service will run on `ws://localhost:8081/ws/market`

### 3.2 Docker Deployment

1. **Create Dockerfile**
   ```dockerfile
   # API service Dockerfile
   FROM golang:1.20-alpine
   WORKDIR /app
   COPY . .
   RUN go mod tidy
   RUN go build -o api cmd/api/main.go
   EXPOSE 8080
   CMD ["./api"]
   ```

   ```dockerfile
   # WebSocket service Dockerfile
   FROM golang:1.20-alpine
   WORKDIR /app
   COPY . .
   RUN go mod tidy
   RUN go build -o ws cmd/ws/main.go
   EXPOSE 8081
   CMD ["./ws"]
   ```

2. **Create Docker Compose file**
   ```yaml
   version: '3'
   services:
     api:
       build:
         context: .
         dockerfile: docker/Dockerfile.api
       ports:
         - "8080:8080"
       restart: always
     ws:
       build:
         context: .
         dockerfile: docker/Dockerfile.ws
       ports:
         - "8081:8081"
       restart: always
   ```

3. **Start services**
   ```bash
   docker-compose up -d
   ```

## 4. API Interfaces

### 4.1 Public Interfaces

- **GET /api/v1/market/ticker**
  - Get latest market trade price and quantity
  - Parameters: symbol (trading pair)
  - Example: `GET http://localhost:8080/api/v1/market/ticker?symbol=BTC/USDT`

- **GET /api/v1/market/depth**
  - Get order book data
  - Parameters: symbol (trading pair), depth (depth, default 30)
  - Example: `GET http://localhost:8080/api/v1/market/depth?symbol=BTC/USDT&depth=30`

### 4.2 Private Interfaces (Local Access Only)

- **POST /api/v1/order/batch**
  - Batch order placement
  - Request body:
    ```json
    {
      "orders": [
        {
          "symbol": "BTC/USDT",
          "side": "buy",
          "type": "limit",
          "price": 50000,
          "quantity": 0.1
        }
      ]
    }
    ```

- **POST /api/v1/order/place**
  - Order placement with price range
  - Request body:
    ```json
    {
      "symbol": "BTC/USDT",
      "side": "buy",
      "type": "limit",
      "start_price": 50000,
      "end_price": 49000,
      "price_step": 100,
      "quantity": 0.01
    }
    ```

- **GET /api/v1/order/list**
  - Get order list
  - Parameters: symbol (trading pair)
  - Example: `GET http://localhost:8080/api/v1/order/list?symbol=BTC/USDT`

- **POST /api/v1/order/cancel**
  - Cancel orders
  - Request body:
    ```json
    {
      "symbol": "BTC/USDT",
      "order_ids": ["order1", "order2"]
    }
    ```

## 5. WebSocket Interfaces

### 5.1 Connection Address
- `ws://localhost:8081/ws/market`

### 5.2 Subscription Message
```json
{
  "action": "subscribe",
  "type": "depth", // or "ticker"
  "symbol": "BTC/USDT"
}
```

### 5.3 Unsubscription Message
```json
{
  "action": "unsubscribe",
  "type": "depth", // or "ticker"
  "symbol": "BTC/USDT"
}
```

### 5.4 Push Messages
- **depth**: 30 levels of order book data
  ```json
  {
    "type": "depth",
    "data": {
      "symbol": "BTC/USDT",
      "bids": [[50000, 1], [49900, 0.5]],
      "asks": [[50100, 0.8], [50200, 1.2]],
      "timestamp": 1630000000000
    }
  }
  ```

- **ticker**: Latest trade price and quantity
  ```json
  {
    "type": "ticker",
    "data": {
      "symbol": "BTC/USDT",
      "price": 50000,
      "quantity": 0.1,
      "timestamp": 1630000000000
    }
  }
  ```

## 6. Security Configuration

### 6.1 Interface Access Control
- Private interfaces only allow local access (127.0.0.1)
- Public interfaces allow public access

### 6.2 Data Transmission Encryption
- Use HTTPS protocol for RESTful API data transmission
- Use WSS protocol for WebSocket data transmission

### 6.3 Prevention of Malicious Requests
- Implement request rate limiting to prevent API abuse
- Strictly validate request parameters to prevent injection attacks

## 7. Monitoring and Logging

### 7.1 Log Configuration
- API service and WebSocket service logs are output to the console
- Log files can be configured as needed

### 7.2 Monitoring
- Integrate Prometheus to monitor the running status of each service
- Use Grafana to display monitoring metrics
- Configure alert mechanisms to detect system exceptions in time

## 8. Performance Optimization

### 8.1 Trading Engine Optimization
- Use in-memory order book to improve matching speed
- Use concurrent processing to improve throughput
- Optimize matching algorithm to reduce computational complexity

### 8.2 API Service Optimization
- Use Gin framework's route grouping and middleware
- Implement request caching to reduce redundant calculations
- Use connection pooling to reduce database connection overhead

### 8.3 WebSocket Service Optimization
- Use goroutine to handle each WebSocket connection
- Implement batch message pushing to reduce network transmission times
- Use compression algorithm to reduce data transmission volume

## 9. Troubleshooting

### 9.1 Common Issues
- **API service cannot start**: Check if the port is occupied, check if dependencies are installed
- **WebSocket connection failed**: Check if the WebSocket service is running, check network connection
- **Order matching failed**: Check if order parameters are correct, check if the trading engine is running normally

### 9.2 Fault Recovery
- After system restart, order book data will be reinitialized
- It is recommended to back up transaction data regularly to facilitate recovery in case of failure

## 10. Extension Suggestions

### 10.1 Function Extension
- Add account system, support user registration and login
- Add K-line data, support technical analysis
- Add transaction history query, support viewing historical trade records

### 10.2 Performance Extension
- Use distributed architecture to improve system scalability
- Use Redis cluster to improve data storage performance
- Use load balancing to improve system concurrent processing capability

## 11. Summary

This project implements a minimalist digital currency exchange that supports both futures and spot trading, providing trading functions and market data through RESTful API and WebSocket. The system is developed in Golang, with high performance and high concurrency characteristics, suitable as a basic framework for digital currency trading.

Through this deployment guide, you can quickly build, deploy, and run the system to start digital currency trading business.