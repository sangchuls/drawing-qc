// Uses the Web Crypto API (not Node's `crypto` module) so this also works
// unmodified inside Next.js middleware, which runs on the Edge runtime.

const SESSION_COOKIE = "dqc_session";
const SESSION_TTL_SECONDS = 60 * 60 * 24 * 14; // 14 days
const UPLOAD_TOKEN_TTL_SECONDS = 60 * 10; // 10 minutes

function toBase64Url(bytes: ArrayBuffer | Uint8Array): string {
  const arr = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  let str = "";
  for (const b of arr) str += String.fromCharCode(b);
  return btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function fromBase64Url(b64url: string): Uint8Array {
  const b64 = b64url.replace(/-/g, "+").replace(/_/g, "/");
  const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
  const str = atob(padded);
  const arr = new Uint8Array(str.length);
  for (let i = 0; i < str.length; i++) arr[i] = str.charCodeAt(i);
  return arr;
}

async function importKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"]
  );
}

async function sign(secret: string, payload: Record<string, unknown>): Promise<string> {
  const body = toBase64Url(new TextEncoder().encode(JSON.stringify(payload)));
  const key = await importKey(secret);
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(body));
  return `${body}.${toBase64Url(sig)}`;
}

async function verify<T extends { exp: number }>(secret: string, token: string): Promise<T | null> {
  const [body, sig] = token.split(".");
  if (!body || !sig) return null;
  const key = await importKey(secret);
  const ok = await crypto.subtle.verify("HMAC", key, fromBase64Url(sig), new TextEncoder().encode(body));
  if (!ok) return null;
  try {
    const payload = JSON.parse(new TextDecoder().decode(fromBase64Url(body))) as T;
    if (Date.now() / 1000 > payload.exp) return null;
    return payload;
  } catch {
    return null;
  }
}

function sessionSecret(): string {
  const s = process.env.SESSION_SECRET;
  if (!s) throw new Error("SESSION_SECRET env var is not set");
  return s;
}

function uploadTokenSecret(): string {
  // shared with the FastAPI backend so it can verify uploads without calling back into Next.js
  const s = process.env.UPLOAD_TOKEN_SECRET;
  if (!s) throw new Error("UPLOAD_TOKEN_SECRET env var is not set");
  return s;
}

export function createSessionToken(): Promise<string> {
  return sign(sessionSecret(), { exp: Date.now() / 1000 + SESSION_TTL_SECONDS });
}

export async function verifySessionToken(token: string | undefined | null): Promise<boolean> {
  if (!token) return false;
  return (await verify<{ exp: number }>(sessionSecret(), token)) !== null;
}

export function createUploadToken(): Promise<string> {
  return sign(uploadTokenSecret(), { exp: Date.now() / 1000 + UPLOAD_TOKEN_TTL_SECONDS });
}

export const SESSION_COOKIE_NAME = SESSION_COOKIE;
