import { afterEach, beforeEach, describe, it, expect } from "vitest";
import { setLocalePreference } from "@/i18n";
import { fmt } from "./format";

// Intl.NumberFormat uses non-breaking spaces (U+202F or U+00A0).
// We strip them before assertions for portability across Node versions.
const normalize = (s: string) => s.replace(/[\u00A0\u202F]/g, " ");

beforeEach(() => setLocalePreference("fr"));
afterEach(() => setLocalePreference("auto"));

describe("fmt.eur", () => {
  it("formats positive amount with euro symbol", () => {
    const r = normalize(fmt.eur(1234.5));
    expect(r).toContain("€");
    expect(r).toMatch(/1.234,50|1 234,50/);
  });

  it("formats zero", () => {
    expect(normalize(fmt.eur(0))).toMatch(/0,00\s?€/);
  });

  it("formats negative amount with minus sign", () => {
    expect(normalize(fmt.eur(-50.25))).toMatch(/-50,25\s?€/);
  });
});

describe("fmt.pct", () => {
  it("formats decimal as percentage with 2 decimals", () => {
    expect(normalize(fmt.pct(0.05))).toMatch(/5,00\s?%/);
  });

  it("handles small decimals", () => {
    expect(normalize(fmt.pct(0.1234))).toMatch(/12,34\s?%/);
  });
});

describe("fmt.signedPct", () => {
  it("shows + sign for positive", () => {
    expect(fmt.signedPct(0.05)).toContain("+");
  });

  it("shows - sign for negative", () => {
    expect(fmt.signedPct(-0.05)).toContain("-");
  });

  it("no sign for zero", () => {
    expect(fmt.signedPct(0)).not.toMatch(/[+-]/);
  });
});

describe("fmt.signedEur", () => {
  it("shows + sign for positive amount", () => {
    expect(fmt.signedEur(1000)).toContain("+");
  });

  it("shows - sign for negative amount", () => {
    expect(fmt.signedEur(-500)).toContain("-");
  });
});

describe("fmt.num", () => {
  it("formats with 2 decimals", () => {
    expect(normalize(fmt.num(3.14159))).toMatch(/3,14/);
  });
});

describe("English locale", () => {
  beforeEach(() => setLocalePreference("en"));

  it("writes euros the British way", () => {
    expect(normalize(fmt.eur(1234.5))).toBe("€1,234.50");
    expect(normalize(fmt.eur0(1234.5))).toBe("€1,235");
    expect(normalize(fmt.signedEur(1000))).toBe("+€1,000.00");
  });

  it("writes percentages with a dot", () => {
    expect(normalize(fmt.pct(0.1234))).toBe("12.34%");
    expect(normalize(fmt.num(3.14159))).toBe("3.14");
  });

  it("abbreviates thousands with the symbol first", () => {
    expect(fmt.kEur(35_000)).toBe("€35k");
    expect(fmt.kEur(3_500)).toBe("€3.5k");
    expect(fmt.kEur(850)).toBe("€850");
    expect(normalize(fmt.approxEur(12_345))).toBe("€12,000");
  });
});

describe("French abbreviations", () => {
  it("keeps the comma and the trailing symbol", () => {
    expect(fmt.kEur(35_000)).toBe("35 k€");
    expect(fmt.kEur(3_500)).toBe("3,5 k€");
    expect(normalize(fmt.approxEur(12_345))).toMatch(/^12 000 €$/);
  });
});
