import { describe, expect, it } from "vitest";

import type { MonthSpending } from "@/api";
import { OTHERS, UNLABELLED, categoryDeltas, monthStack, stackSeries } from "./spending";

function month(key: string, by_category: Record<string, number>, income = 2000): MonthSpending {
  return {
    month: key,
    income,
    total: Object.values(by_category).reduce((s, v) => s + v, 0),
    by_category,
  };
}

const MONTHS: MonthSpending[] = [
  month("2026-06", {
    alimentation: 400,
    restaurant: 200,
    transport: 90,
    loisirs: 50,
    sante: 30,
    voyages: 600,
    autre: 100,
  }),
  month("2026-07", {
    alimentation: 420,
    restaurant: 260,
    transport: 80,
    loisirs: 70,
    sante: 10,
    shopping: 120,
    autre: 80,
  }),
  month("2026-08", {
    alimentation: 380,
    restaurant: 340,
    transport: 100,
    loisirs: 40,
    abonnements: 25,
    autre: 60,
  }),
  month("2026-09", { alimentation: 120, restaurant: 60, autre: 20 }), // current, partial
];

describe("stackSeries", () => {
  it("ranks the labelled categories over the window, then folds, then the unlabelled", () => {
    expect(stackSeries(MONTHS)).toEqual([
      "alimentation",
      "restaurant",
      "voyages",
      "transport",
      "loisirs",
      OTHERS,
      UNLABELLED,
    ]);
  });

  it("has no fold when every category fits in a slot", () => {
    const few = [month("2026-08", { alimentation: 10, restaurant: 5 })];
    expect(stackSeries(few)).toEqual(["alimentation", "restaurant"]);
  });
});

describe("monthStack", () => {
  it("gives every series a value and folds the tail into OTHERS", () => {
    const series = stackSeries(MONTHS);
    expect(monthStack(MONTHS[1], series)).toEqual({
      alimentation: 420,
      restaurant: 260,
      voyages: 0,
      transport: 80,
      loisirs: 70,
      [OTHERS]: 130, // sante 10 + shopping 120
      [UNLABELLED]: 80,
    });
  });
});

describe("categoryDeltas", () => {
  it("compares the last complete month to the average of the earlier ones", () => {
    const report = categoryDeltas(MONTHS);
    expect(report?.month).toBe("2026-08");
    expect(report?.baseline).toBe(2);
    const byCat = Object.fromEntries(report!.rows.map((r) => [r.category, r]));
    expect(byCat.voyages.delta).toBeCloseTo(-300); // 600 once, then nothing
    expect(byCat.restaurant.delta).toBeCloseTo(340 - 230);
    expect(byCat.alimentation.average).toBeCloseTo(410);
    expect(report!.rows[0].category).toBe("voyages"); // biggest move first
    expect(report!.rows.map((r) => r.category)).not.toContain(UNLABELLED);
  });

  it("is null until two complete months exist", () => {
    expect(categoryDeltas(MONTHS.slice(2))).toBeNull();
  });
});
