/**
 * The home-screen widget, seen from the web code (ADR-035).
 *
 * The widget has no session and never calls the backend. The Overview hands
 * it the line it already displays, labels and amounts written in the person's
 * language; the native side stores it in the App Group the widget reads. On
 * the site every function here does nothing.
 */

import { TangentNative, isNative } from "./bridge";

export interface WidgetSnapshot {
  /** « Patrimoine net » / "Net worth", as the tile writes it. */
  label: string;
  /** The amount, already formatted: « 19 600,55 € » or "€19,600.55". */
  value: string;
  /** One line under it, when there is something to say. */
  sub?: string;
  /** Tints the line: true green, false red, left out neutral. */
  positive?: boolean;
}

/** Give the widget what the Overview shows. Never throws: a widget is not the app. */
export async function publishWidgetSnapshot(snapshot: WidgetSnapshot): Promise<void> {
  if (!isNative()) return;
  try {
    await TangentNative.setWidgetSnapshot(snapshot);
  } catch {
    /* no App Group on this build, or the extension is absent: nothing to show */
  }
}

/** Signing out takes the figures off the home screen with the session. */
export async function clearWidgetSnapshot(): Promise<void> {
  if (!isNative()) return;
  try {
    await TangentNative.clearWidgetSnapshot();
  } catch {
    /* same */
  }
}
