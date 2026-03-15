import React from 'react';
import type { TradeItem } from '../hooks/useWebSocket';

const BG = '#161a1e';
const ROW_BG = '#3d4552';
const TEXT = '#eaecef';
const TEXT_MUTED = '#848e9c';
const MONO_FONT = 'ui-monospace, "SF Mono", "Cascadia Code", "Source Code Pro", Menlo, Consolas, monospace';

function formatNum(s: string, decimals: number): string {
  const n = parseFloat(s);
  if (Number.isNaN(n)) return '—';
  if (n >= 1000) return n.toLocaleString('en', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return Number(n.toFixed(decimals)).toString();
}

/** 后端为 UTC 时间戳(ms 或 s)，格式化为本地时间 HH:mm:ss */
function formatTime(ts: number): string {
  const ms = ts < 1e12 ? ts * 1000 : ts;
  const d = new Date(ms);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`;
}

interface LatestTradesProps {
  trades: TradeItem[];
  priceDecimals?: number;
  amountDecimals?: number;
  maxRows?: number;
  style?: React.CSSProperties;
}

export function LatestTrades({
  trades,
  priceDecimals = 2,
  amountDecimals = 4,
  maxRows = 20,
  style,
}: LatestTradesProps) {
  const list = trades.slice(0, maxRows);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
        overflow: 'hidden',
        background: BG,
        borderRadius: 4,
        fontFamily: MONO_FONT,
        ...style,
      }}
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr',
          gap: 6,
          padding: '6px 10px',
          fontSize: 11,
          color: TEXT_MUTED,
          borderBottom: `1px solid ${ROW_BG}`,
          flexShrink: 0,
        }}
      >
        <span style={{ textAlign: 'right' }}>价格</span>
        <span style={{ textAlign: 'right' }}>数量</span>
        <span style={{ textAlign: 'right' }}>时间</span>
      </div>
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', paddingTop: 6 }}>
        {list.length === 0 ? (
          <div style={{ padding: '10px 12px', fontSize: 12, color: TEXT_MUTED, textAlign: 'center' }}>
            暂无成交
          </div>
        ) : (
          list.map((t, i) => (
            <div
              key={`${t.time}-${t.price}-${t.qty}-${i}`}
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr 1fr',
                gap: 6,
                padding: '2px 10px',
                fontSize: 12,
                color: TEXT,
                fontFamily: MONO_FONT,
              }}
            >
              <span style={{ textAlign: 'right' }}>{formatNum(t.price, priceDecimals)}</span>
              <span style={{ textAlign: 'right' }}>{formatNum(t.qty, amountDecimals)}</span>
              <span style={{ textAlign: 'right', color: TEXT_MUTED }}>{formatTime(t.time)}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
