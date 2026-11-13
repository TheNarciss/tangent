import { describe, expect, it } from "vitest";

import type { BankAccountResponse } from "@/api";
import { groupTotal, valueInEur } from "./accounts";

const account = (over: Partial<BankAccountResponse>): BankAccountResponse =>
  ({
    type: "checking",
    currency: "EUR",
    balance: 0,
    valuation: null,
    loan: null,
    ...over,
  }) as BankAccountResponse;

describe("amounts in another currency (ADR-038)", () => {
  it("count in euros at the rate the server sends", () => {
    const sgd = account({ currency: "SGD", balance: 150, to_eur: 1 / 1.5 });
    expect(valueInEur(sgd)).toBeCloseTo(100);
    expect(groupTotal([account({ balance: 1000 }), sgd])).toBeCloseTo(1100);
  });

  it("leave out an account whose currency has no rate", () => {
    const unknown = account({ currency: "VND", balance: 5_000_000, to_eur: null });
    expect(valueInEur(unknown)).toBeNull();
    expect(groupTotal([account({ balance: 20 }), unknown])).toBe(20);
  });

  it("read as euros when the server sends no rate at all", () => {
    expect(groupTotal([account({ balance: 42 })])).toBe(42);
  });
});
