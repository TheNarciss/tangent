/**
 * Responsive helpers — matchMedia-based hooks for layout adaptation.
 *
 * Tailwind breakpoints (kept in sync with tailwind.config.js):
 *   sm  640px
 *   md  768px   ← Tangent's primary mobile/desktop boundary
 *   lg  1024px
 *   xl  1280px
 *
 * Prefer CSS-only responsive design (`md:` prefixes) whenever possible — only
 * reach for these hooks when a structural decision depends on the viewport
 * (e.g. mount a Sheet vs a Dialog, fetch a different payload size).
 */

import { useEffect, useState } from "react";

export const BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
} as const;

/**
 * Returns true if the viewport is narrower than `breakpoint` (default 768px).
 * SSR-safe (returns false on the server).
 *
 * @example
 *   const isMobile = useIsMobile();
 *   return isMobile ? <BottomSheet>...</BottomSheet> : <Dialog>...</Dialog>;
 */
export function useIsMobile(breakpoint: number = BREAKPOINTS.md): boolean {
  const [isMobile, setIsMobile] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return window.innerWidth < breakpoint;
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    const mq = window.matchMedia(`(max-width: ${breakpoint - 1}px)`);
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [breakpoint]);

  return isMobile;
}

export type Breakpoint = "xs" | "sm" | "md" | "lg" | "xl";

/** Returns the current Tailwind breakpoint label. SSR-safe (defaults to "md"). */
export function useBreakpoint(): Breakpoint {
  const resolve = (): Breakpoint => {
    if (typeof window === "undefined") return "md";
    const w = window.innerWidth;
    if (w < BREAKPOINTS.sm) return "xs";
    if (w < BREAKPOINTS.md) return "sm";
    if (w < BREAKPOINTS.lg) return "md";
    if (w < BREAKPOINTS.xl) return "lg";
    return "xl";
  };

  const [bp, setBp] = useState<Breakpoint>(resolve);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const handler = () => setBp(resolve());
    handler();
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, []);

  return bp;
}
