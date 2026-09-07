import { describe, expect, it } from "vitest";
import { publicAsset } from "./assets";

describe("publicAsset", () => {
  it("conserve le préfixe de déploiement GitHub Pages", () => {
    expect(publicAsset("/hero-shopper.jpg", "/SUNU-MALL-V1/")).toBe("/SUNU-MALL-V1/hero-shopper.jpg");
  });

  it("normalise les barres obliques du chemin", () => {
    expect(publicAsset("//logo.png", "/")).toBe("/logo.png");
  });
});
