import type { ApiResponse, DepthData, KlineBar, TickerPrice } from '../types/api';

const BASE = ''; // 使用 Vite proxy 转发到后端

async function request<T>(url: string, params?: Record<string, string | number>): Promise<T> {
  const search = params
    ? '?' + new URLSearchParams(Object.fromEntries(
        Object.entries(params).map(([k, v]) => [k, String(v)])
      )).toString()
    : '';
  const res = await fetch(`${BASE}${url}${search}`);
  const json: ApiResponse<T> = await res.json();
  if (json.code !== 200) {
    throw new Error(json.msg ?? `API error ${json.code}`);
  }
  return json.data as T;
}

/** 获取盘口深度 */
export function fetchDepth(symbol: string, limit = 30): Promise<DepthData> {
  return request<DepthData>('/api/v3/depth', { symbol, limit });
}

/** 获取最新价 */
export function fetchTickerPrice(symbol: string): Promise<TickerPrice> {
  return request<TickerPrice>('/api/v3/ticker/price', { symbol });
}

/** 获取 K 线 */
export function fetchKlines(
  symbol: string,
  interval: string = '1m',
  limit: number = 300
): Promise<KlineBar[]> {
  return request<KlineBar[]>('/api/v3/klines', { symbol, interval, limit });
}
