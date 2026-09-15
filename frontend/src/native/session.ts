/**
 * Finishing a sign-in that ran in the system browser (ADR-035).
 *
 * The browser comes back to `tangent://auth?code=…`; the code, together with
 * the verifier that never left the app, buys the session cookie from the
 * backend. Either the secure browser hands the URL straight back to the
 * caller, or iOS opens the app with it: both paths end here.
 */

import type { QueryClient } from "@tanstack/react-query";
import { App } from "@capacitor/app";

import { exchangeAppCode } from "@/api";
import { t } from "@/i18n";

import { isNative, parseAppReturn, takeVerifier } from "./bridge";

/** Turn the return URL into an open session; the caller may pass the verifier it still holds. */
export async function completeAppReturn(
  url: string,
  qc: QueryClient,
  verifier?: string | null,
): Promise<void> {
  const back = parseAppReturn(url);
  if (!back) return;
  if ("error" in back && back.error) {
    throw new Error(t("system.session.failed", { error: back.error }));
  }
  if (!("code" in back) || !back.code) return;
  const secret = verifier ?? takeVerifier();
  if (!secret) throw new Error(t("system.session.restart"));
  await exchangeAppCode(back.code, secret);
  await qc.invalidateQueries({ queryKey: ["user", "me"] });
}

/** Listen for iOS opening the app with a `tangent://` URL. Returns the unsubscribe. */
export function listenForAppReturn(qc: QueryClient, onError: (e: Error) => void): () => void {
  if (!isNative()) return () => {};
  const handle = App.addListener("appUrlOpen", ({ url }) => {
    completeAppReturn(url, qc).catch((e) => onError(e instanceof Error ? e : new Error(String(e))));
  });
  return () => {
    handle.then((h) => h.remove()).catch(() => {});
  };
}
