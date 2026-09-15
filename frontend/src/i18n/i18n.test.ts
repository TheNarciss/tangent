import { afterEach, describe, expect, it } from "vitest";

import { detectLocale, getLocale, setLocalePreference, t, tn } from "./index";

afterEach(() => setLocalePreference("auto"));

describe("detectLocale", () => {
  it("reads English from the first English variant", () => {
    expect(detectLocale(["en-US", "fr"])).toBe("en");
    expect(detectLocale(["en"])).toBe("en");
  });

  it("defaults to French, including for other languages", () => {
    expect(detectLocale(["fr-FR", "en"])).toBe("fr");
    expect(detectLocale(["de-DE"])).toBe("fr");
    expect(detectLocale([])).toBe("fr");
  });
});

describe("t", () => {
  it("follows the preference and interpolates", () => {
    setLocalePreference("fr");
    expect(getLocale()).toBe("fr");
    expect(t("nav.overview")).toBe("Aperçu");
    expect(t("reset.stepCode", { email: "a@b.c" })).toBe(
      "Code envoyé à a@b.c. Vérifie ta boîte mail.",
    );
    setLocalePreference("en");
    expect(t("nav.overview")).toBe("Overview");
    expect(t("reset.stepCode", { email: "a@b.c" })).toBe("Code sent to a@b.c. Check your inbox.");
  });

  it("leaves an unknown slot untouched", () => {
    setLocalePreference("fr");
    expect(t("reset.stepCode", {})).toContain("{email}");
  });
});

describe("tn", () => {
  it("picks the plural form by the language's rules", () => {
    setLocalePreference("fr");
    expect(tn("account.adminSection.learned", 0)).toMatch(/^0 opération catégorisée/);
    expect(tn("account.adminSection.learned", 1)).toMatch(/^1 opération catégorisée/);
    expect(tn("account.adminSection.learned", 3)).toMatch(/^3 opérations catégorisées/);
    setLocalePreference("en");
    expect(tn("account.adminSection.learned", 0)).toMatch(/^0 transactions/);
    expect(tn("account.adminSection.learned", 1)).toMatch(/^1 transaction /);
  });
});
