import { describe, it, expect } from "vitest";
import { fmt } from "./format";

// Intl.NumberFormat uses non-breaking spaces (U+202F or U+00A0).
// We strip them before assertions for portability across Node versions.
const normalize = (s: string) => s.replace(/[\u00A0\u202F]/g, " ");

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
