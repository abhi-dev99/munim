import { describe, expect, it } from "vitest";
import {
  BLUR_VARIANCE_THRESHOLD,
  GLARE_RATIO_THRESHOLD,
  assessPhotoQuality,
  computeBlurScore,
  computeGlareRatio,
} from "./imageQuality.js";

/**
 * Build a synthetic ImageData-shaped fixture ({ data, width, height }) from a
 * per-pixel RGB generator, without touching canvas/DOM APIs — these tests
 * run in plain Node.
 */
function makeImage(width, height, pixelFn) {
  const data = new Uint8ClampedArray(width * height * 4);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const [r, g, b] = pixelFn(x, y);
      const idx = (y * width + x) * 4;
      data[idx] = r;
      data[idx + 1] = g;
      data[idx + 2] = b;
      data[idx + 3] = 255;
    }
  }
  return { data, width, height };
}

function flatImage(width, height, gray = 128) {
  return makeImage(width, height, () => [gray, gray, gray]);
}

function checkerboardImage(width, height) {
  // Sharp edges (high Laplacian variance) but kept away from 255 so this
  // fixture isolates "in focus" from "overexposed" — a pure 0/255
  // checkerboard would also trip the glare check, which is correct
  // behavior but not what this fixture is testing.
  return makeImage(width, height, (x, y) => {
    const on = (x + y) % 2 === 0;
    const v = on ? 220 : 40;
    return [v, v, v];
  });
}

function nearWhiteImage(width, height, value = 253) {
  return makeImage(width, height, () => [value, value, value]);
}

describe("computeBlurScore", () => {
  it("scores a flat solid-color image as ~zero variance (blurry)", () => {
    const score = computeBlurScore(flatImage(20, 20));
    expect(score).toBe(0);
  });

  it("scores a fine checkerboard pattern as high variance (sharp)", () => {
    const score = computeBlurScore(checkerboardImage(20, 20));
    expect(score).toBeGreaterThan(BLUR_VARIANCE_THRESHOLD * 10);
  });

  it("ranks a sharp image strictly above a flat one", () => {
    const blurry = computeBlurScore(flatImage(20, 20));
    const sharp = computeBlurScore(checkerboardImage(20, 20));
    expect(sharp).toBeGreaterThan(blurry);
  });

  it("handles degenerate tiny images without throwing", () => {
    expect(computeBlurScore({ data: new Uint8ClampedArray(4), width: 1, height: 1 })).toBe(0);
  });
});

describe("computeGlareRatio", () => {
  it("reports ~0 glare for a mid-gray flat image", () => {
    const ratio = computeGlareRatio(flatImage(10, 10, 128));
    expect(ratio).toBe(0);
  });

  it("reports ~1.0 glare ratio for a near-white overexposed image", () => {
    const ratio = computeGlareRatio(nearWhiteImage(10, 10));
    expect(ratio).toBeCloseTo(1, 5);
  });

  it("reports a partial ratio when only some pixels are blown out", () => {
    // Half the image near-white, half mid-gray.
    const img = makeImage(10, 10, (x) => (x < 5 ? [253, 253, 253] : [100, 100, 100]));
    const ratio = computeGlareRatio(img);
    expect(ratio).toBeCloseTo(0.5, 5);
  });
});

describe("assessPhotoQuality", () => {
  it("rejects a flat blurry image with a blur-specific reason", () => {
    const verdict = assessPhotoQuality(flatImage(20, 20, 128));
    expect(verdict.isAcceptable).toBe(false);
    expect(verdict.reason).toMatch(/blur/i);
  });

  it("rejects an overexposed image with a glare-specific reason", () => {
    const verdict = assessPhotoQuality(nearWhiteImage(20, 20));
    expect(verdict.isAcceptable).toBe(false);
    expect(verdict.reason).toMatch(/glare/i);
    expect(verdict.glareRatio).toBeGreaterThan(GLARE_RATIO_THRESHOLD);
  });

  it("accepts a sharp, non-overexposed image with no reason", () => {
    const verdict = assessPhotoQuality(checkerboardImage(20, 20));
    expect(verdict.isAcceptable).toBe(true);
    expect(verdict.reason).toBeNull();
  });
});
