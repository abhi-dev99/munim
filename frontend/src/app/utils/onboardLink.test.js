import { describe, it, expect } from "vitest";
import { extractJoinCode } from "./onboardLink";

describe("extractJoinCode", () => {
  it("pulls the short code out of a well-formed wa.me deep link", () => {
    expect(extractJoinCode("https://wa.me/919876543210?text=JOIN-AB12CD")).toBe("AB12CD");
  });

  it("uppercases a lowercase code", () => {
    expect(extractJoinCode("https://wa.me/919876543210?text=JOIN-ab12cd")).toBe("AB12CD");
  });

  it("matches when JOIN- isn't the first query param", () => {
    expect(extractJoinCode("https://wa.me/919876543210?foo=bar&text=JOIN-XYZ9")).toBe("XYZ9");
  });

  it("returns null for a link with no text param", () => {
    expect(extractJoinCode("https://wa.me/919876543210")).toBeNull();
  });

  it("returns null for an unrelated text param", () => {
    expect(extractJoinCode("https://wa.me/919876543210?text=hello")).toBeNull();
  });

  it("returns null for empty or missing input", () => {
    expect(extractJoinCode("")).toBeNull();
    expect(extractJoinCode(null)).toBeNull();
    expect(extractJoinCode(undefined)).toBeNull();
  });
});
