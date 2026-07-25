import { describe, expect, it } from "vitest";
import { cn, formatPrice, formatDate } from "./utils";

describe("cn", () => {
  it("merges class names and drops falsy values", () => {
    expect(cn("a", false, "b", undefined, "c")).toBe("a b c");
  });
});

describe("formatPrice", () => {
  it("formats a numeric amount as XOF currency", () => {
    const result = formatPrice(6000);
    expect(result).toContain("6");
    expect(result).toMatch(/XOF|CFA/);
  });

  it("parses a string amount the same way as a number", () => {
    expect(formatPrice("6000")).toBe(formatPrice(6000));
  });

  it("has no decimal places (whole XOF amounts)", () => {
    const result = formatPrice(1234.5);
    expect(result).not.toContain(".5");
    expect(result).not.toContain(",5");
  });
});

describe("formatDate", () => {
  it("formats an ISO date string without throwing", () => {
    expect(() => formatDate("2026-07-19T10:30:00Z")).not.toThrow();
  });

  it("produces a non-empty, human-readable string", () => {
    const result = formatDate("2026-07-19T10:30:00Z");
    expect(result.length).toBeGreaterThan(0);
  });
});
