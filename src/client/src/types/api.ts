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

/** API 通用响应 */
export interface ApiResponse<T> {
  code: number;
  data?: T;
  msg?: string;
}
