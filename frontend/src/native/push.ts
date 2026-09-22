/**
 * « Préviens-moi quand mon briefing est prêt » (ADR-037).
 *
 * Three things have to agree: iOS must allow it, Apple must hand the app an
 * address for this phone, and the backend must know that address. The switch
 * in « Mon compte » drives all three, and turning it off forgets the address
 * server-side rather than fighting the system setting.
 *
 * On the site every function here reports « rien à faire » and does nothing.
 */

import { forgetDevice, registerDevice } from "@/api";

import { TangentNative, isNative } from "./bridge";

export interface PushState {
  /** iOS allows notifications for Tangent. */
  granted: boolean;
  /** Never asked yet: asking will show the system prompt. */
  askable: boolean;
  /** Apple's address for this phone, empty until it is registered. */
  token: string;
}

const OFF: PushState = { granted: false, askable: false, token: "" };

export async function pushState(): Promise<PushState> {
  if (!isNative()) return OFF;
  try {
    return await TangentNative.pushStatus();
  } catch {
    return OFF;
  }
}

/** Ask iOS, then tell the backend where to reach this phone. */
export async function enablePush(): Promise<PushState> {
  if (!isNative()) return OFF;
  try {
    const { granted, token } = await TangentNative.requestPushPermission();
    if (granted && token) await registerDevice(token);
    return { granted, askable: false, token: token ?? "" };
  } catch {
    return OFF;
  }
}

/** Stop announcing: the backend forgets the address, iOS keeps its setting. */
export async function disablePush(): Promise<void> {
  if (!isNative()) return;
  try {
    const { token } = await TangentNative.pushStatus();
    if (token) await forgetDevice(token);
  } catch {
    /* nothing registered, nothing to forget */
  }
}

/**
 * At every launch: Apple can hand out a new address for the same phone, and
 * the language may have changed since last time. Silent, best effort.
 */
export async function syncPushOnLaunch(): Promise<void> {
  if (!isNative()) return;
  try {
    const { granted, token } = await TangentNative.pushStatus();
    if (granted && token) await registerDevice(token);
  } catch {
    /* not allowed, or no address yet: nothing to sync */
  }
}
