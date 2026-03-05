import React from 'react';
import type { DepthLevel } from '../types/api';

const BID_COLOR = '#0ecb81';
const ASK_COLOR = '#f6465d';
const BG = '#0b0e11';
const ROW_BG = '#161a1e';
const TEXT = '#eaecef';
const TEXT_MUTED = '#848e9c';

function formatNum(s: string, decimals: number): string {
  const n = parseFloat(s);
  if (Number.isNaN(n)) return '—';
  if (n >= 1000) return n.toLocaleString('en', { maximumFractionDigits: decimals });
  return Number(n.toFixed(decimals)).toString();
}

function depthRows(
  levels: DepthLevel[],
  side: 'bid' | 'ask',
  maxTotal: number,
  priceDecimals: number,
  amountDecimals: number
) {
  let total = 0;
  return levels.map(([price, amount]) => {
    total += parseFloat(price) * parseFloat(amount);
    const pct = maxTotal > 0 ? (total / maxTotal) * 100 : 0;
    const color = side === 'bid' ? BID_COLOR : ASK_COLOR;
    return (
      <div
        key={price}
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr',
          gap: 8,
          padding: '4px 12px',
          fontSize: 13,
          position: 'relative',
          zIndex: 1,
        }}
      >
        <span style={{ textAlign: 'right', color }}>{formatNum(price, priceDecimals)}</span>
        <span style={{ textAlign: 'right', color: TEXT }}>{formatNum(amount, amountDecimals)}</span>
        <span style={{ textAlign: 'right', color: TEXT_MUTED }}>{formatNum(String(total), 2)}</span>
        {/* 深度条从中间往两侧展开：卖盘从右往左，买盘从左往右 */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: side === 'bid' ? 0 : undefined,
            right: side === 'ask' ? 0 : undefined,
            bottom: 0,
            width: `${pct}%`,
            marginLeft: side === 'ask' ? 'auto' : undefined,
            marginRight: side === 'bid' ? 'auto' : undefined,
            backgroundColor: side === 'bid' ? 'rgba(14, 203, 129, 0.08)' : 'rgba(246, 70, 93, 0.08)',
            zIndex: 0,
            pointerEvents: 'none',
          }}
        />
      </div>
    );
  });
}

interface OrderBookProps {
  bids: DepthLevel[];
  asks: DepthLevel[];
  lastPrice?: string;
  priceDecimals?: number;
  amountDecimals?: number;
  maxRows?: number;
  style?: React.CSSProperties;
}

export function OrderBook({
  bids,
  asks,
  lastPrice,
  priceDecimals = 2,
  amountDecimals = 4,
  maxRows = 15,
  style,
}: OrderBookProps) {
  const bidSlice = bids.slice(0, maxRows);
  const askSlice = asks.slice(0, maxRows);

  let maxTotal = 0;
  let run = 0;
  for (const [p, q] of bidSlice) {
    run += parseFloat(p) * parseFloat(q);
    if (run > maxTotal) maxTotal = run;
  }
  run = 0;
  for (const [p, q] of askSlice) {
    run += parseFloat(p) * parseFloat(q);
    if (run > maxTotal) maxTotal = run;
  }

  return (
    <div
      style={{
        background: BG,
        borderRadius: 8,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
        ...style,
      }}
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr',
          gap: 8,
          padding: '10px 12px',
          fontSize: 12,
          color: TEXT_MUTED,
          borderBottom: `1px solid ${ROW_BG}`,
          flexShrink: 0,
        }}
      >
        <span style={{ textAlign: 'right' }}>价格</span>
        <span style={{ textAlign: 'right' }}>数量</span>
        <span style={{ textAlign: 'right' }}>累计</span>
      </div>

      {/* 上：卖盘，底部对齐，最佳卖紧贴中间 */}
      <div
        style={{
          flex: 1,
          minHeight: 0,
          overflow: 'auto',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'flex-end',
        }}
      >
        {depthRows([...askSlice].reverse(), 'ask', maxTotal, priceDecimals, amountDecimals)}
      </div>

      {lastPrice != null && lastPrice !== '' && !Number.isNaN(parseFloat(lastPrice)) && (
        <div
          style={{
            padding: '8px 12px',
            fontSize: 18,
            fontWeight: 600,
            textAlign: 'center',
            color: TEXT,
            borderTop: `1px solid ${ROW_BG}`,
            borderBottom: `1px solid ${ROW_BG}`,
            flexShrink: 0,
          }}
        >
          {formatNum(lastPrice, priceDecimals)}
        </div>
      )}

      {/* 下：买盘，价格从高到低，最佳买（最高买价）在顶部紧贴中间 */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
        {depthRows(bidSlice, 'bid', maxTotal, priceDecimals, amountDecimals)}
      </div>
    </div>
  );
}
