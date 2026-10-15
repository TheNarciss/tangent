/**
 * The native side of the iPhone app (ADR-035), as the web code sees it.
 *
 * On the site every function here is a no-op or a plain browser call, so the
 * same React code runs in both places. `TangentNative` is the small Swift
 * plugin shipped in ios/App/App/TangentNativePlugin.swift.
 */

import { Capacitor, registerPlugin } from "@capacitor/core";

export interface TangentNativePlugin {
  /** Face ID / Touch ID, with the device passcode as fallback. */
  unlock(options: { reason: string }): Promise<{ available: boolean; success: boolean }>;
  /** An OAuth round trip in the system's secure browser; resolves with the callback URL. */
  authSession(options: { url: string; callbackScheme: string }): Promise<{ url: string }>;
  /** Sign in with Apple through iOS itself. */
  appleSignIn(options: { nonce: string }): Promise<{ identityToken: string }>;
  /** Hand the home-screen widget the line the Overview shows. */
  setWidgetSnapshot(options: {
    label: string;
    value: string;
    sub?: string;
    positive?: boolean;
  }): Promise<{ written: boolean }>;
  /** Take the figures off the home screen (sign-out). */
  clearWidgetSnapshot(): Promise<void>;
  /** Ask iOS for notifications, then wait for Apple's address for this phone. */
  requestPushPermission(): Promise<{ granted: boolean; token?: string }>;
  /** What iOS allows today, and the address if there is one. */
  pushStatus(): Promise<{ granted: boolean; askable: boolean; token: string }>;
}

export const TangentNative = registerPlugin<TangentNativePlugin>("TangentNative");

/** True inside the iPhone app, false on the site. */
export function isNative(): boolean {
  return Capacitor.isNativePlatform();
}

export const APP_SCHEME = "tangent";
export const AUTH_RETURN_HOST = "auth";

/** What a `tangent://auth?…` URL carries back into the app, or null for any other URL. */
export function parseAppReturn(
  url: string,
): { code: string } | { error: string } | { code?: undefined; error?: undefined } | null {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return null;
  }
  if (parsed.protocol !== `${APP_SCHEME}:` || parsed.host !== AUTH_RETURN_HOST) return null;
  const code = parsed.searchParams.get("code");
  if (code) return { code };
  const error = parsed.searchParams.get("error");
  if (error) return { error };
  return {};
}

/* ── PKCE: the verifier stays in the app, the challenge travels ───────────── */

const VERIFIER_KEY = "tangent.pkce.verifier";

function base64url(bytes: Uint8Array): string {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function makeVerifier(): string {
  const bytes = new Uint8Array(48);
  crypto.getRandomValues(bytes);
  return base64url(bytes); // 64 characters, within PKCE's 43..128
}

export async function challengeOf(verifier: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return base64url(new Uint8Array(digest));
}

/** Keep the verifier for the callback that will come back, in this app instance only. */
export function rememberVerifier(verifier: string): void {
  try {
    sessionStorage.setItem(VERIFIER_KEY, verifier);
  } catch {
    /* private mode: the caller still holds it in memory for the direct return */
  }
}

export function takeVerifier(): string | null {
  try {
    const v = sessionStorage.getItem(VERIFIER_KEY);
    sessionStorage.removeItem(VERIFIER_KEY);
    return v;
  } catch {
    return null;
  }
}
