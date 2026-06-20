import React, { useEffect, useState } from 'react';
import { login } from '../utils/auth';

const BG = '#161a1e';
const BORDER = '#3d4552';
const TEXT = '#eaecef';
const MUTED = '#848e9c';
const ACCENT = '#f0b90b';

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

interface LoginModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function LoginModal({ open, onClose, onSuccess }: LoginModalProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setUsername('');
      setPassword('');
      setError('');
      setSubmitting(false);
    }
  }, [open]);

  if (!open) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const result = login(username.trim(), password);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    setSubmitting(true);
    onSuccess();
    onClose();
  };

  return (
    <div
      role="presentation"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.55)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="login-title"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 320,
          background: BG,
          border: `1px solid ${BORDER}`,
          borderRadius: 6,
          padding: 20,
          boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
        }}
      >
        <div id="login-title" style={{ color: TEXT, fontSize: 15, fontWeight: 600, marginBottom: 4 }}>
          登录
        </div>
        <div style={{ color: MUTED, fontSize: 11, marginBottom: 16 }}>
          登录态本地保存 10 分钟
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <div style={{ color: MUTED, fontSize: 11, marginBottom: 4 }}>账号</div>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="demo"
              autoFocus
              style={INPUT_STYLE}
            />
          </div>
          <div>
            <div style={{ color: MUTED, fontSize: 11, marginBottom: 4 }}>密码</div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              style={INPUT_STYLE}
            />
          </div>

          {error && <div style={{ color: '#f6465d', fontSize: 12 }}>{error}</div>}

          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                flex: 1,
                border: `1px solid ${BORDER}`,
                borderRadius: 4,
                background: '#0b0e11',
                color: MUTED,
                padding: '8px 10px',
                fontSize: 13,
                cursor: 'pointer',
              }}
            >
              取消
            </button>
            <button
              type="submit"
              disabled={submitting}
              style={{
                flex: 1,
                border: 'none',
                borderRadius: 4,
                background: ACCENT,
                color: '#0b0e11',
                padding: '8px 10px',
                fontSize: 13,
                fontWeight: 600,
                cursor: submitting ? 'not-allowed' : 'pointer',
                opacity: submitting ? 0.7 : 1,
              }}
            >
              登录
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
