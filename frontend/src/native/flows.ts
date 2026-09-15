/**
 * The flows that leave the app and come back (ADR-035): Google, Apple, the banks.
 *
 * On the site each one is a page navigation and a return URL the callback
 * handlers read from the address bar. In the app the same URL opens in the
 * system's secure browser and comes back as `tangent://…`; the query of that
 * URL is put where the same handlers look for it.
 */

import type { QueryClient } from "@tanstack/react-query";
import type { NavigateFunction } from "react-router-dom";

import { API_URL, signInWithAppleToken, startAppleLogin, startGoogleLogin } from "@/api";

import {
  APP_SCHEME,
  TangentNative,
  challengeOf,
  isNative,
  makeVerifier,
  rememberVerifier,
} from "./bridge";
import { completeAppReturn } from "./session";

/** The query string a `tangent://banks?…` (or any `tangent://`) return carries, or null. */
export function searchOfReturn(url: string): string | null {
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== `${APP_SCHEME}:`) return null;
    return parsed.search;
  } catch {
    return null;
  }
}

/** Leave for the bank's consent page and come back to where the callback handlers look. */
export async function openExternalFlow(url: string, navigate: NavigateFunction): Promise<void> {
  if (!isNative()) {
    window.location.href = url;
    return;
  }
  const back = await TangentNative.authSession({ url, callbackScheme: APP_SCHEME });
  const search = searchOfReturn(back.url);
  if (search === null) throw new Error("Retour inattendu du navigateur.");
  navigate({ pathname: "/", search }, { replace: true });
}

/** Which platform the backend should send the bank's answer back to. */
export function platform(): "web" | "app" {
  return isNative() ? "app" : "web";
}

/** Google: the site navigates away; the app runs the PKCE round trip and opens the session. */
export async function signInWithGoogle(qc: QueryClient): Promise<void> {
  if (!isNative()) {
    await startGoogleLogin();
    return;
  }
  const verifier = makeVerifier();
  rememberVerifier(verifier);
  const challenge = await challengeOf(verifier);
  const back = await TangentNative.authSession({
    url: `${API_URL}/auth/app/google/start?challenge=${challenge}`,
    callbackScheme: APP_SCHEME,
  });
  await completeAppReturn(back.url, qc, verifier);
}

/** Apple: the site navigates away; the app asks iOS and posts the id_token. */
export async function signInWithApple(qc: QueryClient): Promise<void> {
  if (!isNative()) {
    await startAppleLogin();
    return;
  }
  const raw = makeVerifier();
  const hashed = await sha256Hex(raw);
  const result = await TangentNative.appleSignIn({ nonce: hashed });
  await signInWithAppleToken(result.identityToken, hashed);
  await qc.invalidateQueries({ queryKey: ["user", "me"] });
}

async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}
