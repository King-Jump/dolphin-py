const STORAGE_KEY = 'dolphin_auth';
const SESSION_MS = 10 * 60 * 1000;

interface AuthSession {
  username: string;
  expiresAt: number;
}

function readSession(): AuthSession | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const session = JSON.parse(raw) as AuthSession;
    if (!session.username || typeof session.expiresAt !== 'number') {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    if (Date.now() >= session.expiresAt) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return session;
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function isLoggedIn(): boolean {
  return readSession() !== null;
}

export function getUsername(): string | null {
  return readSession()?.username ?? null;
}

export function login(
  username: string,
  password: string,
): { ok: true } | { ok: false; error: string } {
  if (username === 'demo' && password === '123456') {
    const session: AuthSession = {
      username,
      expiresAt: Date.now() + SESSION_MS,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    return { ok: true };
  }
  return { ok: false, error: '账号或密码错误' };
}
