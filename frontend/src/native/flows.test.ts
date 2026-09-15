import { describe, expect, it } from "vitest";

import { platform, searchOfReturn } from "./flows";

describe("a bank's return into the app", () => {
  it("keeps the query the callback handlers read", () => {
    expect(searchOfReturn("tangent://banks?enablebanking=success")).toBe("?enablebanking=success");
    expect(searchOfReturn("tangent://banks?powens_sync=error&error=no_access_token")).toBe(
      "?powens_sync=error&error=no_access_token",
    );
    expect(searchOfReturn("https://riskybusinesses.uk/?enablebanking=success")).toBeNull();
    expect(searchOfReturn("garbage")).toBeNull();
  });

  it("is the site under test", () => {
    expect(platform()).toBe("web");
  });
});
