/** K线单条 */
export interface KlineBar {
  ot: number;
  o: string;
  h: string;
  l: string;
  c: string;
  v: string;
  ct: number;
  a: string;
}

/** 深度档位 [价格, 数量] */
export type DepthLevel = [string, string];

/** 深度数据 */
export interface DepthData {
  lastUpdateId: number;
  bids: DepthLevel[];
  asks: DepthLevel[];
}

/** 最新价 */
export interface TickerPrice {
  symbol: string;
  price: string;
  quantity: string;
}

export type OrderSide = 'BUY' | 'SELL';
export type OrderType = 'LIMIT' | 'MARKET';

export interface NewOrderRequest {
  symbol: string;
  side: OrderSide;
  type: OrderType;
  quantity: string;
  price?: string;
  client_order_id?: string;
}

export interface NewOrderResult {
  symbol: string;
  orderId: string | number;
  clientOrderId: string;
  transactTime: number;
  price: string | number;
  origQty: string | number;
  executedQty: string | number;
  status: string;
  type: string;
  side: string;
}

/** API 通用响应 */
export interface ApiResponse<T> {
  code: number;
  data?: T;
  msg?: string;
}
