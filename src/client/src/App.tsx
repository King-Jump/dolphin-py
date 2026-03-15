import React, { useEffect, useState } from 'react';
import { fetchDepth, fetchKlines, fetchTickerPrice } from './api/client';
import { KlineChart } from './components/KlineChart';
import { LatestTrades } from './components/LatestTrades';
import { OrderBook } from './components/OrderBook';
import { useWebSocket } from './hooks/useWebSocket';
import type { DepthLevel, KlineBar } from './types/api';
import { sortBids, sortAsks } from './utils/orderBook';

const SYMBOLS = ['BTCUSDT', 'JPMUSDT', 'ETHUSDT'] as const;
type SymbolType = (typeof SYMBOLS)[number];

function getSymbolFromUrl(): SymbolType {
  const params = new URLSearchParams(location.search);
  const s = params.get('symbol')?.toUpperCase();
  if (s && (SYMBOLS as readonly string[]).includes(s)) return s as SymbolType;
  return 'BTCUSDT';
}

function setSymbolInUrl(symbol: SymbolType): void {
  const url = new URL(location.href);
  url.searchParams.set('symbol', symbol);
  window.history.replaceState(null, '', url.pathname + url.search);
}

const INTERVALS = ['1m', '1h', '1d'] as const;
const KLINE_LIMIT = 250;

const INTERVAL_MS: Record<(typeof INTERVALS)[number], number> = {
  '1m': 60 * 1000,
  '1h': 60 * 60 * 1000,
  '1d': 24 * 60 * 60 * 1000,
};

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
  justifyContent: 'space-between',
  gap: 24,
  padding: '10px 20px',
  borderBottom: '1px solid #3d4552',
  flexWrap: 'wrap',
  background: '#0b0e11',
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
  borderRight: '1px solid #3d4552',
  minHeight: 0,
  flex: 1,
};

const TICKER_STYLE: React.CSSProperties = {
  fontSize: 22,
  fontWeight: 600,
  color: '#eaecef',
  letterSpacing: '-0.02em',
};

const SYMBOL_STYLE: React.CSSProperties = {
  fontSize: 12,
  color: '#848e9c',
  marginBottom: 2,
};

const INTERVAL_BTN = (active: boolean): React.CSSProperties => ({
  padding: '5px 10px',
  fontSize: 12,
  border: '1px solid #3d4552',
  borderRadius: 4,
  background: active ? '#2b3139' : 'transparent',
  color: active ? '#f0b90b' : '#848e9c',
  cursor: 'pointer',
  fontWeight: 500,
});

const SYMBOL_BTN = (active: boolean): React.CSSProperties => ({
  padding: '5px 10px',
  fontSize: 12,
  border: '1px solid #3d4552',
  borderRadius: 4,
  background: active ? '#2b3139' : 'transparent',
  color: active ? '#f0b90b' : '#848e9c',
  cursor: 'pointer',
  fontWeight: 500,
});

export default function App() {
  const [symbol, setSymbolState] = useState<SymbolType>(getSymbolFromUrl);

  const setSymbol = (s: SymbolType) => {
    setSymbolState(s);
    setSymbolInUrl(s);
  };
  const [interval, setInterval] = useState<(typeof INTERVALS)[number]>('1m');
  const [klines, setKlines] = useState<KlineBar[]>([]);
  const [depth, setDepth] = useState<{ bids: DepthLevel[]; asks: DepthLevel[] }>({ bids: [], asks: [] });
  const [tickerPrice, setTickerPrice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { depth: wsDepth, lastTrade, recentTrades } = useWebSocket(symbol);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setTickerPrice(null);
    setKlines([]);
    setDepth({ bids: [], asks: [] });
    Promise.all([
      fetchKlines(symbol, interval, KLINE_LIMIT),
      fetchDepth(symbol, 30),
    ])
      .then(([k, d]) => {
        if (cancelled) return;
        setKlines(k);
        setDepth({ bids: sortBids(d.bids ?? []), asks: sortAsks(d.asks ?? []) });
      })
      .catch((e) => {
        if (!cancelled) setError(e?.message ?? '请求失败');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    fetchTickerPrice(symbol)
      .then((t) => {
        if (!cancelled) setTickerPrice(t.price);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [symbol, interval]);

  useEffect(() => {
    if (wsDepth.bids.length > 0 || wsDepth.asks.length > 0) {
      setDepth({ bids: wsDepth.bids, asks: wsDepth.asks });
    }
  }, [wsDepth]);

  useEffect(() => {
    if (lastTrade?.price) setTickerPrice(lastTrade.price);
  }, [lastTrade]);

  // 根据成交推送实时更新 K 线：命中已有 bar 则更新 h/l/c/v，否则若进入新周期则追加新 bar
  useEffect(() => {
    if (!lastTrade || !klines.length) return;
    const intervalMs = INTERVAL_MS[interval];
    const t = lastTrade.time < 1e12 ? lastTrade.time * 1000 : lastTrade.time;
    const price = parseFloat(lastTrade.price);
    const qty = parseFloat(lastTrade.qty);
    if (Number.isNaN(price) || Number.isNaN(qty)) return;
    setKlines((prev) => {
      const idx = prev.findIndex((b) => t >= b.ot && t < b.ot + intervalMs);
      if (idx !== -1) {
        const bar = prev[idx];
        const newH = String(Math.max(parseFloat(bar.h), price));
        const newL = String(Math.min(parseFloat(bar.l), price));
        const newV = String(parseFloat(bar.v) + qty);
        const next = [...prev];
        next[idx] = { ...bar, h: newH, l: newL, c: lastTrade.price, v: newV };
        return next;
      }
      const lastBar = prev[prev.length - 1];
      if (t < lastBar.ot + intervalMs) return prev;
      const newOt = Math.floor(t / intervalMs) * intervalMs;
      const newBar: KlineBar = {
        ot: newOt,
        o: lastTrade.price,
        h: lastTrade.price,
        l: lastTrade.price,
        c: lastTrade.price,
        v: lastTrade.qty,
        ct: newOt + intervalMs - 1,
        a: '',
      };
      const next = [...prev, newBar];
      return next.length > KLINE_LIMIT ? next.slice(-KLINE_LIMIT) : next;
    });
  }, [lastTrade, interval]);

  const displayPrice = tickerPrice ?? (klines.length ? klines[klines.length - 1].c : '—');

  return (
    <div style={PAGE_STYLE}>
      <header style={HEADER_STYLE}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <div>
            <div style={SYMBOL_STYLE}>{symbol}</div>
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
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {SYMBOLS.map((s) => (
            <button
              key={s}
              style={SYMBOL_BTN(s === symbol)}
              onClick={() => setSymbol(s)}
              type="button"
            >
              {s}
            </button>
          ))}
        </div>
      </header>

      {error && (
        <div style={{ padding: '10px 20px', fontSize: 13, background: 'rgba(246, 70, 93, 0.12)', color: '#f6465d', borderBottom: '1px solid #3d4552' }}>
          网络错误，请重试
        </div>
      )}

      <div style={LAYOUT_STYLE}>
        <div style={CHART_PANEL_STYLE}>
          {loading && !klines.length ? (
            <div style={{ padding: 40, textAlign: 'center', fontSize: 13, color: '#848e9c' }}>加载 K 线中…</div>
          ) : (
            <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
              <KlineChart data={klines.slice(-KLINE_LIMIT)} />
            </div>
          )}
        </div>
        <div
          style={{
            padding: '12px 16px',
            minWidth: 280,
            height: '100%',
            minHeight: 0,
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
            background: '#0b0e11',
            borderLeft: '1px solid #3d4552',
          }}
        >
          <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            <div style={{ fontSize: 12, color: '#ffffff', marginBottom: 6, flexShrink: 0, fontWeight: 500 }}>订单薄</div>
            <OrderBook
              bids={depth.bids}
              asks={depth.asks}
              lastPrice={displayPrice}
              priceDecimals={2}
              amountDecimals={4}
              style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}
            />
          </div>
          <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            <div style={{ fontSize: 12, color: '#ffffff', marginBottom: 6, flexShrink: 0, fontWeight: 500 }}>最新成交</div>
            <LatestTrades
              trades={recentTrades}
              priceDecimals={2}
              amountDecimals={4}
              maxRows={20}
              style={{ flex: 1, minHeight: 0 }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
