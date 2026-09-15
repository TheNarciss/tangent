import type { CapacitorConfig } from "@capacitor/cli";

/**
 * The iPhone app is the web build in a native shell (ADR-035).
 *
 * HTTP goes through the phone's native stack (CapacitorHttp): the backend's
 * session cookie is stored and sent back like a browser would, so the same
 * cookie authentication serves the site and the app. Build the bundle with
 * VITE_API_URL=https://riskybusinesses.uk/api before `cap sync`.
 */
const config: CapacitorConfig = {
  appId: "uk.riskybusinesses.tangent",
  appName: "Tangent",
  webDir: "dist",
  ios: {
    contentInset: "automatic",
    backgroundColor: "#0a0a0a",
  },
  plugins: {
    CapacitorHttp: { enabled: true },
    CapacitorCookies: { enabled: true },
  },
};

export default config;
