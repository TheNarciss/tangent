import { describe, it, expect } from "vitest";
import { cn } from "./utils";

describe("cn", () => {
  it("merges class names with spaces", () => {
    expect(cn("foo", "bar")).toBe("foo bar");
  });

  it("filters falsy values (false, null, undefined, empty)", () => {
    expect(cn("foo", false, "bar", null, undefined, "")).toBe("foo bar");
  });

  it("dedupes conflicting tailwind classes via twMerge (last wins)", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
    expect(cn("text-red-500", "text-blue-500")).toBe("text-blue-500");
  });

  it("supports conditional objects (clsx pattern)", () => {
    expect(cn("base", { active: true, disabled: false })).toBe("base active");
  });
});
