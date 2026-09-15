import { describe, expect, it } from "vitest";

import { challengeOf, isNative, makeVerifier, parseAppReturn } from "./bridge";

describe("the app's return URL", () => {
  it("reads a code or an error, and nothing else", () => {
    expect(parseAppReturn("tangent://auth?code=abc.def")).toEqual({ code: "abc.def" });
    expect(parseAppReturn("tangent://auth?error=400")).toEqual({ error: "400" });
    expect(parseAppReturn("tangent://auth")).toEqual({});
    expect(parseAppReturn("tangent://other?code=x")).toBeNull();
    expect(parseAppReturn("https://riskybusinesses.uk/?code=x")).toBeNull();
    expect(parseAppReturn("not a url")).toBeNull();
  });
});

describe("PKCE", () => {
  it("makes a verifier of the right shape and its S256 challenge", async () => {
    const verifier = makeVerifier();
    expect(verifier).toMatch(/^[A-Za-z0-9_-]{43,128}$/);
    expect(makeVerifier()).not.toBe(verifier);
    // Known vector from RFC 7636 appendix B.
    const challenge = await challengeOf("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk");
    expect(challenge).toBe("E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM");
  });
});

describe("platform", () => {
  it("is the site under test", () => {
    expect(isNative()).toBe(false);
  });
});
