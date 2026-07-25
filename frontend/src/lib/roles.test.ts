import { describe, expect, it } from "vitest";
import { roleHomePath } from "./roles";

describe("roleHomePath", () => {
  it("sends an admin to /admin regardless of other roles", () => {
    expect(roleHomePath(["client", "admin"])).toBe("/admin");
  });

  it("sends a merchant to /merchant", () => {
    expect(roleHomePath(["merchant"])).toBe("/merchant");
  });

  it("sends a driver to /driver-dashboard", () => {
    expect(roleHomePath(["driver"])).toBe("/driver-dashboard");
  });

  it("prioritizes admin over merchant and driver", () => {
    expect(roleHomePath(["driver", "merchant", "admin"])).toBe("/admin");
  });

  it("prioritizes merchant over driver", () => {
    expect(roleHomePath(["driver", "merchant"])).toBe("/merchant");
  });

  it("defaults a plain client (or no roles) to /home", () => {
    expect(roleHomePath(["client"])).toBe("/home");
    expect(roleHomePath([])).toBe("/home");
  });
});
