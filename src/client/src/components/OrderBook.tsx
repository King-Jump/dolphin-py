import React, { useEffect, useRef, useState } from 'react';
import type { DepthLevel } from '../types/api';
import { sortBids, sortAsks } from '../utils/orderBook';

const ROW_HEIGHT_PX = 20;
const HEADER_HEIGHT_PX = 28;
const CURRENT_PRICE_HEIGHT_PX = 32;

function calcMaxRowsFromHeight(containerHeight: number, hasCurrentPrice: boolean): number {
  const fixed = HEADER_HEIGHT_PX + (hasCurrentPrice ? CURRENT_PRICE_HEIGHT_PX : 0);
  const forOneSide = (containerHeight - fixed) / 2;
  const rows = Math.floor(forOneSide / ROW_HEIGHT_PX);
  return Math.max(1, rows);
}

const BID_COLOR = '#0ecb81';
const ASK_COLOR = '#f6465d';
const BG = '#161a1e';
const ROW_BG = '#3d4552';
const TEXT = '#eaecef';
const TEXT_MUTED = '#848e9c';
const HEADER_TEXT = '#848e9c';
const MONO_FONT = 'ui-monospace, "SF Mono", "Cascadia Code", "Source Code Pro", Menlo, Consolas, monospace';

function formatNum(s: string, decimals: number): string {
  const n = parseFloat(s);
  if (Number.isNaN(n)) return '—';
  if (n >= 1000) return n.toLocaleString('en', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
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
          gap: 6,
          padding: '2px 10px',
          fontSize: 12,
          position: 'relative',
          zIndex: 1,
        }}
      >
        <span style={{ textAlign: 'right', color, fontFamily: MONO_FONT }}>{formatNum(price, 2)}</span>
        <span style={{ textAlign: 'right', color: TEXT, fontFamily: MONO_FONT }}>{formatNum(amount, amountDecimals)}</span>
        <span style={{ textAlign: 'right', color: TEXT_MUTED, fontFamily: MONO_FONT }}>{formatNum(String(total), 2)}</span>
        {/* 深度条：卖盘从右往左，买盘从右往左（右侧对齐） */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: undefined,
            right: 0,
            bottom: 0,
            width: `${pct}%`,
            marginLeft: 'auto',
            backgroundColor: side === 'bid' ? 'rgba(14, 203, 129, 0.12)' : 'rgba(246, 70, 93, 0.12)',
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
  maxRows: maxRowsProp,
  style,
}: OrderBookProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [maxRows, setMaxRows] = useState(() =>
    typeof maxRowsProp === 'number' ? maxRowsProp : 10
  );

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const { height } = entries[0]?.contentRect ?? { height: 0 };
      const hasPrice =
        lastPrice != null && lastPrice !== '' && !Number.isNaN(parseFloat(lastPrice));
      setMaxRows(calcMaxRowsFromHeight(height, hasPrice));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [lastPrice]);

  useEffect(() => {
    if (typeof maxRowsProp === 'number') setMaxRows(maxRowsProp);
  }, [maxRowsProp]);

  const bidSlice = sortBids(bids).slice(0, maxRows);
  const askSlice = sortAsks(asks).slice(0, maxRows);

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
      ref={containerRef}
      style={{
        background: BG,
        borderRadius: 4,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
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
          color: HEADER_TEXT,
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
          overflow: 'hidden',
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
            padding: '6px 10px',
            fontSize: 16,
            fontWeight: 600,
            textAlign: 'center',
            color: TEXT,
            background: 'rgba(43, 49, 57, 0.5)',
            borderTop: `1px solid ${ROW_BG}`,
            borderBottom: `1px solid ${ROW_BG}`,
            flexShrink: 0,
          }}
        >
          {formatNum(lastPrice, 2)}
        </div>
      )}

      {/* 下：买盘，价格从高到低，最佳买（最高买价）在顶部紧贴中间 */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {depthRows(bidSlice, 'bid', maxTotal, priceDecimals, amountDecimals)}
      </div>
    </div>
  );
}
