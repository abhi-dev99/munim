import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

// A broken manifest.json fails PWA installability with no error visible
// anywhere in the app — a browser just silently declines to offer
// "Add to Home Screen". This is the only signal that would ever catch it.
const manifestPath = join(
  dirname(fileURLToPath(import.meta.url)),
  "..",
  "..",
  "public",
  "manifest.json"
);
const manifest = JSON.parse(readFileSync(manifestPath, "utf-8"));

describe("trader PWA manifest", () => {
  it("is valid, parseable JSON", () => {
    expect(manifest).toBeTypeOf("object");
  });

  it("has the fields a browser's installability check requires", () => {
    expect(manifest.name).toBeTruthy();
    expect(manifest.short_name).toBeTruthy();
    expect(manifest.start_url).toBeTruthy();
    expect(manifest.display).toBe("standalone");
    expect(manifest.background_color).toMatch(/^#[0-9a-fA-F]{6}$/);
    expect(manifest.theme_color).toMatch(/^#[0-9a-fA-F]{6}$/);
  });

  it("points start_url and scope at the trader app, not the CA dashboard", () => {
    expect(manifest.start_url).toBe("/trader");
    expect(manifest.scope).toBe("/trader");
  });

  it("declares at least a 192px and 512px icon", () => {
    const sizes = manifest.icons.map((icon) => icon.sizes);
    expect(sizes).toContain("192x192");
    expect(sizes).toContain("512x512");
  });

  it("declares a maskable icon variant for adaptive home-screen icons", () => {
    const maskable = manifest.icons.find((icon) => icon.purpose === "maskable");
    expect(maskable).toBeTruthy();
  });
});
