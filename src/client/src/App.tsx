import React, { useEffect, useState } from 'react';
import { fetchDepth, fetchKlines, fetchTickerPrice } from './api/client';
import { KlineChart } from './components/KlineChart';
import { OrderBook } from './components/OrderBook';
import { useWebSocket } from './hooks/useWebSocket';
import type { DepthLevel, KlineBar } from './types/api';
import { sortBids, sortAsks, mergeDepth } from './utils/orderBook';

const SYMBOL = 'BTCUSDT';
const INTERVALS = ['1m', '1h', '1d'] as const;
const KLINE_LIMIT = 300;

const PAGE_STYLE: React.CSSProperties = {
  width: '100%',
  height: '100%',
  minHeight: '100vh',
  background: '#0b0e11',
  color: '#eaecef',
  fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
  display: 'flex',
  flexDirection: 'column',
  boxSizing: 'border-box',
};

const HEADER_STYLE: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 24,
  padding: '12px 24px',
  borderBottom: '1px solid #2b3139',
  flexWrap: 'wrap',
};

const LAYOUT_STYLE: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1fr 320px',
  gap: 0,
  flex: 1,
  minHeight: 0,
  overflow: 'hidden',
};

const CHART_PANEL_STYLE: React.CSSProperties = {
  padding: 16,
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
  borderRight: '1px solid #2b3139',
  minHeight: 0,
  flex: 1,
};

const TICKER_STYLE: React.CSSProperties = {
  fontSize: 24,
  fontWeight: 700,
  color: '#eaecef',
};

const SYMBOL_STYLE: React.CSSProperties = {
  fontSize: 14,
  color: '#848e9c',
};

const INTERVAL_BTN = (active: boolean): React.CSSProperties => ({
  padding: '6px 12px',
  fontSize: 12,
  border: '1px solid #2b3139',
  borderRadius: 4,
  background: active ? '#2b3139' : 'transparent',
  color: active ? '#f0b90b' : '#848e9c',
  cursor: 'pointer',
});

export default function App() {
  const [interval, setInterval] = useState<(typeof INTERVALS)[number]>('1m');
  const [klines, setKlines] = useState<KlineBar[]>([]);
  const [depth, setDepth] = useState<{ bids: DepthLevel[]; asks: DepthLevel[] }>({ bids: [], asks: [] });
  const [tickerPrice, setTickerPrice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { depth: wsDepth, lastTrade } = useWebSocket(SYMBOL);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([
      fetchKlines(SYMBOL, interval, KLINE_LIMIT),
      fetchDepth(SYMBOL, 30),
      fetchTickerPrice(SYMBOL),
    ])
      .then(([k, d, t]) => {
        if (cancelled) return;
        setKlines(k);
        setDepth({ bids: sortBids(d.bids ?? []), asks: sortAsks(d.asks ?? []) });
        setTickerPrice(t.price);
      })
      .catch((e) => {
        if (!cancelled) setError(e?.message ?? '请求失败');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [interval]);

  useEffect(() => {
    if (wsDepth.bids.length > 0 || wsDepth.asks.length > 0) {
      setDepth((prev) =>
        mergeDepth(prev.bids, prev.asks, wsDepth.bids, wsDepth.asks)
      );
    }
  }, [wsDepth]);

  useEffect(() => {
    if (lastTrade?.price) setTickerPrice(lastTrade.price);
  }, [lastTrade]);

  const displayPrice = tickerPrice ?? (klines.length ? klines[klines.length - 1].c : '—');

  return (
    <div style={PAGE_STYLE}>
      <header style={HEADER_STYLE}>
        <div>
          <div style={SYMBOL_STYLE}>{SYMBOL}</div>
          <div style={TICKER_STYLE}>{displayPrice}</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {INTERVALS.map((i) => (
            <button
              key={i}
              style={INTERVAL_BTN(i === interval)}
              onClick={() => setInterval(i)}
              type="button"
            >
              {i === '1m' ? '1 分钟' : i === '1h' ? '1 小时' : '1 天'}
            </button>
          ))}
        </div>
      </header>

      {error && (
        <div style={{ padding: 16, background: '#3d1f1f', color: '#f6465d' }}>
          网络错误，请重试
        </div>
      )}

      <div style={LAYOUT_STYLE}>
        <div style={CHART_PANEL_STYLE}>
          {loading && !klines.length ? (
            <div style={{ padding: 40, textAlign: 'center', color: '#848e9c' }}>加载 K 线中…</div>
          ) : (
            <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
              <KlineChart data={klines} />
            </div>
          )}
        </div>
        <div
          style={{
            padding: 16,
            minWidth: 280,
            height: '100%',
            minHeight: 0,
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div style={{ fontSize: 12, color: '#848e9c', marginBottom: 8, flexShrink: 0 }}>盘口深度</div>
          <OrderBook
            bids={depth.bids}
            asks={depth.asks}
            lastPrice={displayPrice}
            priceDecimals={2}
            amountDecimals={4}
            maxRows={15}
            style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}
          />
        </div>
      </div>
    </div>
  );
}
