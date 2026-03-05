import { useEffect, useRef, useState } from 'react';
import type { DepthLevel } from '../types/api';

const WS_BASE = `ws://3.1.221.68:8765/spot`;

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

export function useWebSocket(symbol: string | null) {
  const [depth, setDepth] = useState<{ bids: DepthLevel[]; asks: DepthLevel[] }>({ bids: [], asks: [] });
  const [lastTrade, setLastTrade] = useState<{ price: string; qty: string } | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const symbolRef = useRef(symbol);

  symbolRef.current = symbol;

  useEffect(() => {
    if (!symbol) return;

    const ws = new WebSocket(WS_BASE);
    wsRef.current = ws;

    ws.onopen = () => {
      const sub = symbol.toLowerCase();
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
          if (payload.s?.toUpperCase() === symbolRef.current?.toUpperCase()) {
            setDepth((prev) => ({
              bids: payload.b?.length ? payload.b : prev.bids,
              asks: payload.a?.length ? payload.a : prev.asks,
            }));
          }
        } else if (msg.e === 'trade') {
          const payload = msg as TradeUpdate;
          if (payload.s?.toUpperCase() === symbolRef.current?.toUpperCase()) {
            setLastTrade({ price: payload.p, qty: payload.q });
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
    };
  }, [symbol]);

  return { depth, lastTrade };
}
