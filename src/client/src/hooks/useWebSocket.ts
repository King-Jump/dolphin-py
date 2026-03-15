import { useEffect, useRef, useState } from 'react';
import type { DepthLevel } from '../types/api';
import { sortBids, sortAsks } from '../utils/orderBook';

const WS_BASE = `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//3.1.221.68:8765/spot`;

export interface DepthUpdate {
  e: 'depthUpdate';
  s: string;
  b: DepthLevel[];
  a: DepthLevel[];
}

export interface TradeUpdate {
  e: 'trade';
  s: string;
  p: string;
  q: string;
  C: number;
}

const RECENT_TRADES_MAX = 20;

export interface TradeItem {
  price: string;
  qty: string;
  time: number;
}

export function useWebSocket(symbol: string | null) {
  const [depth, setDepth] = useState<{ bids: DepthLevel[]; asks: DepthLevel[] }>({ bids: [], asks: [] });
  const [lastTrade, setLastTrade] = useState<TradeItem | null>(null);
  const [recentTrades, setRecentTrades] = useState<TradeItem[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const symbolRef = useRef(symbol);

  symbolRef.current = symbol;

  useEffect(() => {
    if (!symbol) return;

    const ws = new WebSocket(WS_BASE);
    wsRef.current = ws;

    ws.onopen = () => {
      const sub = symbol.toUpperCase();
      ws.send(
        JSON.stringify({
          method: 'SUBSCRIBE',
          params: [`${sub}@depth`, `${sub}@trade`],
          id: 1,
        })
      );
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string);
        if (msg.e === 'depthUpdate') {
          const payload = msg as DepthUpdate;
          if (payload.s?.toUpperCase() !== symbolRef.current?.toUpperCase()) return;
          const b = payload.b ?? [];
          const a = payload.a ?? [];
          // WS 推送为有限档位全量快照，直接替换
          setDepth({ bids: sortBids(b), asks: sortAsks(a) });
        } else if (msg.e === 'trade') {
          const payload = msg as TradeUpdate;
          if (payload.s?.toUpperCase() === symbolRef.current?.toUpperCase()) {
            const item: TradeItem = { price: payload.p, qty: payload.q, time: payload.C ?? Date.now() };
            setLastTrade(item);
            setRecentTrades((prev) => [item, ...prev].slice(0, RECENT_TRADES_MAX));
          }
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onerror = () => {};
    ws.onclose = () => {};

    return () => {
      ws.close();
      wsRef.current = null;
      setDepth({ bids: [], asks: [] });
      setLastTrade(null);
      setRecentTrades([]);
    };
  }, [symbol]);

  return { depth, lastTrade, recentTrades };
}
