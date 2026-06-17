import React, { useState } from 'react';
import { createOrder } from '../api/client';
import type { NewOrderResult, OrderSide, OrderType } from '../types/api';

const BG = '#161a1e';
const BORDER = '#3d4552';
const TEXT = '#eaecef';
const MUTED = '#848e9c';
const BUY = '#0ecb81';
const SELL = '#f6465d';

const INPUT_STYLE: React.CSSProperties = {
  width: '100%',
  boxSizing: 'border-box',
  background: '#0b0e11',
  border: `1px solid ${BORDER}`,
  color: TEXT,
  borderRadius: 4,
  padding: '8px 10px',
  fontSize: 12,
  outline: 'none',
};

interface OrderEntryProps {
  symbol: string;
  pricePlaceholder?: string;
}

export function OrderEntry({ symbol, pricePlaceholder }: OrderEntryProps) {
  const [side, setSide] = useState<OrderSide>('BUY');
  const [type, setType] = useState<OrderType>('LIMIT');
  const [price, setPrice] = useState('');
  const [quantity, setQuantity] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState<string>('');
  const [result, setResult] = useState<NewOrderResult | null>(null);

  const submit = async () => {
    setMsg('');
    setResult(null);
    if (!quantity.trim()) {
      setMsg('请输入数量');
      return;
    }
    if (type === 'LIMIT' && !price.trim()) {
      setMsg('限价单请输入价格');
      return;
    }
    try {
      setSubmitting(true);
      const res = await createOrder({
        symbol,
        side,
        type,
        quantity: quantity.trim(),
        ...(type === 'LIMIT' ? { price: price.trim() } : {}),
      });
      setResult(res);
      setMsg('下单成功');
      setQuantity('');
      if (type === 'LIMIT') setPrice('');
    } catch (e) {
      setMsg(e instanceof Error ? e.message : '下单失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        background: BG,
        border: `1px solid ${BORDER}`,
        borderRadius: 4,
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
        padding: 12,
        gap: 10,
      }}
    >
      <div style={{ display: 'flex', gap: 8 }}>
        <button
          type="button"
          onClick={() => setSide('BUY')}
          style={{
            flex: 1,
            border: `1px solid ${BORDER}`,
            borderRadius: 4,
            background: side === 'BUY' ? 'rgba(14,203,129,0.18)' : '#0b0e11',
            color: side === 'BUY' ? BUY : MUTED,
            padding: '6px 8px',
            fontSize: 12,
            cursor: 'pointer',
          }}
        >
          买入
        </button>
        <button
          type="button"
          onClick={() => setSide('SELL')}
          style={{
            flex: 1,
            border: `1px solid ${BORDER}`,
            borderRadius: 4,
            background: side === 'SELL' ? 'rgba(246,70,93,0.18)' : '#0b0e11',
            color: side === 'SELL' ? SELL : MUTED,
            padding: '6px 8px',
            fontSize: 12,
            cursor: 'pointer',
          }}
        >
          卖出
        </button>
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <button
          type="button"
          onClick={() => setType('LIMIT')}
          style={{
            flex: 1,
            border: `1px solid ${BORDER}`,
            borderRadius: 4,
            background: type === 'LIMIT' ? '#2b3139' : '#0b0e11',
            color: type === 'LIMIT' ? '#f0b90b' : MUTED,
            padding: '6px 8px',
            fontSize: 12,
            cursor: 'pointer',
          }}
        >
          限价
        </button>
        <button
          type="button"
          onClick={() => setType('MARKET')}
          style={{
            flex: 1,
            border: `1px solid ${BORDER}`,
            borderRadius: 4,
            background: type === 'MARKET' ? '#2b3139' : '#0b0e11',
            color: type === 'MARKET' ? '#f0b90b' : MUTED,
            padding: '6px 8px',
            fontSize: 12,
            cursor: 'pointer',
          }}
        >
          市价
        </button>
      </div>

      {type === 'LIMIT' && (
        <div>
          <div style={{ color: MUTED, fontSize: 11, marginBottom: 4 }}>价格</div>
          <input
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder={pricePlaceholder || '请输入价格'}
            style={INPUT_STYLE}
          />
        </div>
      )}

      <div>
        <div style={{ color: MUTED, fontSize: 11, marginBottom: 4 }}>数量</div>
        <input
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          placeholder="请输入数量"
          style={INPUT_STYLE}
        />
      </div>

      <button
        type="button"
        onClick={submit}
        disabled={submitting}
        style={{
          border: 'none',
          borderRadius: 4,
          background: side === 'BUY' ? BUY : SELL,
          color: '#fff',
          padding: '8px 10px',
          fontSize: 13,
          cursor: submitting ? 'not-allowed' : 'pointer',
          opacity: submitting ? 0.7 : 1,
        }}
      >
        {submitting ? '提交中…' : `${side === 'BUY' ? '买入' : '卖出'} ${symbol}`}
      </button>

      {(msg || result) && (
        <div style={{ borderTop: `1px solid ${BORDER}`, paddingTop: 8 }}>
          {msg && <div style={{ color: msg.includes('成功') ? BUY : SELL, fontSize: 12 }}>{msg}</div>}
          {result && (
            <div style={{ color: MUTED, fontSize: 11, marginTop: 4 }}>
              订单号: {result.orderId} / 状态: {result.status}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
