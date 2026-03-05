# Digital Currency Exchange API Documentation

## 1. Spot API

### 1.1 Private Endpoints (Local Access Only)

#### 1.1.1 Create Order
- **Endpoint**: `POST /api/v3/order`
- **Permission**: Local access only
- **Request Parameters**:
  | Parameter | Type | Required | Description |
  |-----------|------|----------|-------------|
  | symbol | string | Yes | Trading pair, e.g., BTCUSDT |
  | side | string | Yes | Order side, BUY or SELL |
  | type | string | Yes | Order type, LIMIT or MARKET |
  | quantity | string | Yes | Order quantity |
  | price | string | No | Order price (required for limit orders) |
  | client_order_id | string | No | User-defined order ID |

- **Response**:
  ```json
  {
    "code": 200,
    "data": {
      "symbol": "BTCUSDT",
      "orderId": 12345,
      "clientOrderId": "abc123",
      "transactTime": 1617295200000,
      "price": "59000.00",
      "origQty": "1.0",
      "executedQty": "0.0",
      "status": "NEW",
      "type": "LIMIT",
      "side": "BUY"
    }
  }
  ```

#### 1.1.2 Batch Create Orders
- **Endpoint**: `POST /api/v3/batchOrders`
- **Permission**: Local access only
- **Request Parameters**:
  | Parameter | Type | Required | Description |
  |-----------|------|----------|-------------|
  | batchOrders | array | Yes | Order array, each element contains the parameters for creating an order as described above |

Order Element Definition
  | Parameter | Type | Required | Description |
  |-----------|------|----------|-------------|
  | symbol | string | Yes | Trading pair, e.g., BTCUSDT |
  | side | string | Yes | Order side, BUY or SELL |
  | type | string | Yes | Order type, LIMIT or MARKET |
  | quantity | string | Yes | Order quantity |
  | price | string | No | Order price (required for limit orders) |
  | client_order_id | string | No | User-defined order ID |
- **Response**:
  ```json
  {
    "code": 200,
    "data": [
      {
        "symbol": "BTCUSDT",
        "orderId": 12345,
        "clientOrderId": "abc123",
        "transactTime": 1617295200000,
        "price": "59000.00",
        "origQty": "1.0",
        "executedQty": "0.0",
        "status": "NEW",
        "type": "LIMIT",
        "side": "BUY"
      }
    ]
  }
  ```

#### 1.1.3 Cancel Orders
- **Endpoint**: `DELETE /api/v3/order`
- **Permission**: Local access only
- **Request Parameters**:
  | Parameter | Type | Required | Description |
  |-----------|------|----------|-------------|
  | symbol | string | Yes | Trading pair, e.g., BTCUSDT |
  | orderIds | string | Yes | Order ID list, separated by commas |
- **Response**:
  ```json
  {
    "code": 200,
    "data": [
      {
        "symbol": "BTCUSDT",
        "orderId": 12345,
        "status": "CANCELED"
      }
    ]
  }
  ```

#### 1.1.4 Get Open Orders
- **Endpoint**: `GET /api/v3/openOrders`
- **Permission**: Local access only
- **Request Parameters**:
  | Parameter | Type | Required | Description |
  |-----------|------|----------|-------------|
  | symbol | string | No | Trading pair, e.g., BTCUSDT |
- **Response**:
  ```json
  {
    "code": 200,
    "data": [
      {
        "symbol": "BTCUSDT",
        "orderId": 12345,
        "clientOrderId": "abc123",
        "price": "59000.00",
        "origQty": "1.0",
        "executedQty": "0.0",
        "status": "NEW",
        "type": "LIMIT",
        "side": "BUY"
      }
    ]
  }
  ```

#### 1.1.5 Mock Trade
- **Endpoint**: `POST /api/v3/mock`
- **Permission**: Local access only
- **Request Parameters**:
  | Parameter | Type | Required | Description |
  |-----------|------|----------|-------------|
  | symbol | string | Yes | Trading pair, e.g., BTCUSDT |
  | side | string | Yes | Trade direction, e.g., BUY, SELL |
  | price | string | Yes | Mock trade price |
  | quantity | string | Yes | Mock trade quantity |
- **Response**:
  ```json
  {
    "code": 200,
    "data": {
      "symbol": "BTCUSDT",
      "price": "59000.00",
      "quantity": "1.0",
      "status": "FILLED"
    }
  }
  ```

### 1.2 Public Endpoints

#### 1.2.1 Get Order Book Depth
- **Endpoint**: `GET /api/v3/depth`
- **Permission**: Public
- **Request Parameters**:
  | Parameter | Type | Required | Description |
  |-----------|------|----------|-------------|
  | symbol | string | Yes | Trading pair, e.g., BTCUSDT |
  | limit | integer | No | Depth quantity, default 30 |
- **Response**:
  ```json
  {
    "code": 200,
    "data": {
      "lastUpdateId": 1617295200000,
      "bids": [
        ["59000.00", "1.0"],
        ["58999.00", "2.0"]
      ],
      "asks": [
        ["59001.00", "1.0"],
        ["59002.00", "2.0"]
      ]
    }
  }
  ```

#### 1.2.2 Get Latest Price
- **Endpoint**: `GET /api/v3/ticker/price`
- **Permission**: Public
- **Request Parameters**:
  | Parameter | Type | Required | Description |
  |-----------|------|----------|-------------|
  | symbol | string | Yes | Trading pair, e.g., BTCUSDT |
- **Response**:
  ```json
  {
    "code": 200,
    "data": {
      "symbol": "BTCUSDT",
      "price": "59000.00",
      "quantity": "10.00"
    }
  }
  ```

#### 1.2.3 Get Kline Data
- **Endpoint**: `GET /api/v3/klines`
- **Permission**: Public
- **Request Parameters**:
  | Parameter | Type | Required | Description |
  |-----------|------|----------|-------------|
  | symbol | string | Yes | Trading pair, e.g., BTCUSDT |
  | interval | string | No | Kline interval, default 1m |
  | limit | integer | No | Depth quantity, default 10 |
- **Response**:
  ```json
  {
    "code": 200,
    "data": [
      {
        "ot": 1617295200000,  // Open time
        "o": "58950.00",     // Open price
        "h": "59200.00",     // High price
        "l": "58800.00",     // Low price
        "c": "59100.00",     // Close price
        "v": "10.5",         // Volume
        "ct": 1617295799999,   // Close time
        "a": "619575.00",    // Quote asset volume
      }
    ]
  }
  ```

## 2. Futures API

### 2.1 Private Endpoints (Local Access Only)

#### 2.1.1 Create Order
- **Endpoint**: `POST /fapi/v1/order`
- **Permission**: Local access only
- **Request Parameters**:
  | Parameter | Type | Required | Description |
  |-----------|------|----------|-------------|
  | symbol | string | Yes | Trading pair, e.g., BTCUSDT |
  | side | string | Yes | Order side, BUY or SELL |
  | type | string | Yes | Order type, LIMIT or MARKET |
  | quantity | string | Yes | Order quantity |
  | price | string | No | Order price (required for limit orders) |
  | client_order_id | string | No | User-defined order ID |
- **Response**:
  ```json
  {
    "code": 200,
    "data": {
      "symbol": "BTCUSDT",
      "orderId": 12345,
      "clientOrderId": "abc123",
      "transactTime": 1617295200000,
      "price": "59000.00",
      "origQty": "1.0",
      "executedQty": "0.0",
      "status": "NEW",
      "type": "LIMIT",
      "side": "BUY"
    }
  }
  ```

#### 2.1.2 Batch Create Orders
- **Endpoint**: `POST /fapi/v1/batchOrders`
- **Permission**: Local access only
- **Request Parameters**:
  | Parameter | Type | Required | Description |
  |-----------|------|----------|-------------|
  | batchOrders | array | Yes | Order array, each element contains the parameters for creating an order as described above |

Order Element Definition
  | Parameter | Type | Required | Description |
  |-----------|------|----------|-------------|
  | symbol | string | Yes | Trading pair, e.g., BTCUSDT |
  | side | string | Yes | Order side, BUY or SELL |
  | type | string | Yes | Order type, LIMIT or MARKET |
  | quantity | string | Yes | Order quantity |
  | price | string | No | Order price (required for limit orders) |
  | client_order_id | string | No | User-defined order ID |
- **Response**:
  ```json
  {
    "code": 200,
    "data": [
      {
        "symbol": "BTCUSDT",
        "orderId": 12345,
        "clientOrderId": "abc123",
        "transactTime": 1617295200000,
        "price": "59000.00",
        "origQty": "1.0",
        "executedQty": "0.0",
        "status": "NEW",
        "type": "LIMIT",
        "side": "BUY"
      }
    ]
  }
  ```

#### 2.1.3 Cancel Orders
- **Endpoint**: `DELETE /fapi/v1/order`
- **Permission**: Local access only
- **Request Parameters**:
  | Parameter | Type | Required | Description |
  |-----------|------|----------|-------------|
  | symbol | string | Yes | Trading pair, e.g., BTCUSDT |
  | orderIds | string | Yes | Order ID list, separated by commas |
- **Response**:
  ```json
  {
    "code": 200,
    "data": [
      {
        "symbol": "BTCUSDT",
        "orderId": 12345,
        "status": "CANCELED"
      }
    ]
  }
  ```

#### 2.1.4 Get Open Orders
- **Endpoint**: `GET /fapi/v1/openOrders`
- **Permission**: Local access only
- **Request Parameters**:
  | Parameter | Type | Required | Description |
  |-----------|------|----------|-------------|
  | symbol | string | No | Trading pair, e.g., BTCUSDT |
- **Response**:
  ```json
  {
    "code": 200,
    "data": [
      {
        "symbol": "BTCUSDT",
        "orderId": 12345,
        "clientOrderId": "abc123",
        "price": "59000.00",
        "origQty": "1.0",
        "executedQty": "0.0",
        "status": "NEW",
        "type": "LIMIT",
        "side": "BUY"
      }
    ]
  }
  ```

#### 2.1.5 Mock Trade
- **Endpoint**: `POST /fapi/v3/mock`
- **Permission**: Local access only
- **Request Parameters**:
  | Parameter | Type | Required | Description |
  |-----------|------|----------|-------------|
  | symbol | string | Yes | Trading pair, e.g., BTCUSDT |
  | side | string | Yes | Trade direction, e.g., BUY, SELL |
  | price | string | Yes | Mock trade price |
  | quantity | string | Yes | Mock trade quantity |
- **Response**:
  ```json
  {
    "code": 200,
    "data": {
      "symbol": "BTCUSDT",
      "price": "59000.00",
      "quantity": "1.0",
      "status": "FILLED"
    }
  }
  ```

### 2.2 Public Endpoints

#### 2.2.1 Get Order Book Depth
- **Endpoint**: `GET /fapi/v1/depth`
- **Permission**: Public
- **Request Parameters**:
  | Parameter | Type | Required | Description |
  |-----------|------|----------|-------------|
  | symbol | string | Yes | Trading pair, e.g., BTCUSDT |
  | limit | integer | No | Depth quantity, default 30 |
- **Response**:
  ```json
  {
    "code": 200,
    "data": {
      "lastUpdateId": 1617295200000,
      "bids": [
        ["59000.00", "1.0"],
        ["58999.00", "2.0"]
      ],
      "asks": [
        ["59001.00", "1.0"],
        ["59002.00", "2.0"]
      ]
    }
  }
  ```

#### 2.2.2 Get Latest Price
- **Endpoint**: `GET /fapi/v1/ticker/price`
- **Permission**: Public
- **Request Parameters**:
  | Parameter | Type | Required | Description |
  |-----------|------|----------|-------------|
  | symbol | string | Yes | Trading pair, e.g., BTCUSDT |
- **Response**:
  ```json
  {
    "code": 200,
    "data": {
      "symbol": "BTCUSDT",
      "price": "59000.00",
      "quantity": "10.00"
    }
  }
  ```

#### 2.2.3 Get Kline Data
- **Endpoint**: `GET /fapi/v1/klines`
- **Permission**: Public
- **Request Parameters**:
  | Parameter | Type | Required | Description |
  |-----------|------|----------|-------------|
  | symbol | string | Yes | Trading pair, e.g., BTCUSDT |
  | interval | string | No | Kline interval, default 1m |
  | limit | integer | No | Depth quantity, default 10 |
- **Response**:
  ```json
  {
    "code": 200,
    "data": [
      {
        "ot": 1617295200000,  // Open time
        "o": "58950.00",     // Open price
        "h": "59200.00",     // High price
        "l": "58800.00",     // Low price
        "c": "59100.00",     // Close price
        "v": "10.5",         // Volume
        "ct": 1617295799999,   // Close time
        "a": "619575.00",    // Quote asset volume
      }
    ]
  }
  ```

## 3. WebSocket API

### 3.1 Connection Address
- **Address**: `ws://localhost:8765` (Local access)
- **Public Address**: `ws://[Server IP]:8765` (Public access)

### 3.2 Subscription Message
```json
{
  "method": "SUBSCRIBE",
  "params": [
    "btcusdt@depth",
    "btcusdt@trade"
  ],
  "id": 1
}
```

### 3.3 Depth Update Message
```json
{
  "e": "depthUpdate",
  "E": 1617295200000,
  "s": "BTCUSDT",
  "U": 12345,
  "u": 12345,
  "b": [
    ["59000.00", "1.0"],
    ["58999.00", "2.0"]
  ],
  "a": [
    ["59001.00", "1.0"],
    ["59002.00", "2.0"]
  ]
}
```

### 3.4 Trade Update Message
```json
{
  "e": "trade",
  "E": 1617295200000, # event timestamp
  "s": "BTCUSDT",     # symbol
  "id": 12345,        # trade id
  "p": "0.0",         # price
  "q": "0.0",         # quantity
  "C": 1617295200000, # trade timestamp
}
```