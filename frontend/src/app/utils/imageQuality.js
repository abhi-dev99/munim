/**
 * On-device photo-quality checks for the invoice camera scanner.
 *
 * Why this exists: the backend OCR pipeline (llm_router.py, invoice_agent.py)
 * already has fallback logic for garbled/unreadable Gemini Vision output —
 * blurry or glare-washed invoice photos are a known, real failure mode, not a
 * hypothetical. Running a cheap, classic computer-vision check entirely on
 * the phone, before the photo is ever uploaded, catches that failure mode
 * instantly and for free instead of paying for an OCR call that was doomed
 * from the start.
 *
 * Every function below is pure and operates on a plain ImageData-shaped
 * object ({ data: Uint8ClampedArray, width, height }) rather than the DOM,
 * so they can run and be unit-tested in plain Node with synthetic fixtures —
 * no canvas or browser APIs required at test time.
 */

// --- Tunable thresholds -------------------------------------------------

// Laplacian-variance floor below which a photo is treated as "too blurry to
// OCR reliably". Flat/out-of-focus regions produce a near-zero second
// derivative everywhere (variance near 0); crisp printed text and invoice
// rule lines produce sharp edges with variance in the hundreds to
// thousands. This is tuned against the downscaled analysis frame the
// scanner draws before extracting ImageData (see trader/page.js), not the
// full-resolution capture.
export const BLUR_VARIANCE_THRESHOLD = 60;

// A pixel is considered "blown out" by glare/flash reflection when every
// RGB channel exceeds this value (max 255).
export const GLARE_CHANNEL_THRESHOLD = 250;

// Fraction of blown-out pixels above which a photo is flagged for glare.
export const GLARE_RATIO_THRESHOLD = 0.15;

/**
 * Convert RGBA ImageData pixel data to a flat grayscale buffer using
 * ITU-R BT.601 luma weights.
 * @param {{data: Uint8ClampedArray|number[], width: number, height: number}} imageData
 * @returns {Float32Array}
 */
function toGrayscale(imageData) {
  const { data, width, height } = imageData;
  const gray = new Float32Array(width * height);
  for (let i = 0, p = 0; p < gray.length; i += 4, p++) {
    gray[p] = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
  }
  return gray;
}

/**
 * Sharpness metric based on the variance of a 3x3 discrete Laplacian
 * (second-derivative edge operator) applied to the grayscale image. This is
 * the same classic "Laplacian variance" technique used by real document
 * scanner apps to reject blurry captures. Low variance = few/weak edges =
 * likely blurry. High variance = strong edges = likely in focus.
 * @param {{data: Uint8ClampedArray|number[], width: number, height: number}} imageData
 * @returns {number}
 */
export function computeBlurScore(imageData) {
  const { width, height } = imageData;
  if (!width || !height || width < 3 || height < 3) return 0;

  const gray = toGrayscale(imageData);
  const interiorCount = (width - 2) * (height - 2);
  if (interiorCount <= 0) return 0;

  // Single pass: accumulate sum and sum-of-squares of the Laplacian
  // response directly, no need to materialize a second full-size buffer.
  let sum = 0;
  let sumSq = 0;

  for (let y = 1; y < height - 1; y++) {
    const row = y * width;
    for (let x = 1; x < width - 1; x++) {
      const idx = row + x;
      const value =
        gray[idx - width] + gray[idx + width] + gray[idx - 1] + gray[idx + 1] - 4 * gray[idx];
      sum += value;
      sumSq += value * value;
    }
  }

  const mean = sum / interiorCount;
  const variance = sumSq / interiorCount - mean * mean;
  return Math.max(0, variance);
}

/**
 * Fraction of pixels that are near-fully overexposed (all RGB channels
 * above GLARE_CHANNEL_THRESHOLD) — a proxy for blown-out glare/flash
 * reflection washing out the printed text on a document.
 * @param {{data: Uint8ClampedArray|number[], width: number, height: number}} imageData
 * @returns {number}
 */
export function computeGlareRatio(imageData) {
  const { data } = imageData;
  const totalPixels = data.length / 4;
  if (totalPixels === 0) return 0;

  let blownOut = 0;
  for (let i = 0; i < data.length; i += 4) {
    if (
      data[i] > GLARE_CHANNEL_THRESHOLD &&
      data[i + 1] > GLARE_CHANNEL_THRESHOLD &&
      data[i + 2] > GLARE_CHANNEL_THRESHOLD
    ) {
      blownOut++;
    }
  }
  return blownOut / totalPixels;
}

/**
 * Combined verdict on whether a captured photo is likely to OCR reliably.
 * Glare is checked first because a badly blown-out region also reads as
 * "low variance" (flat white), and glare is the more actionable, specific
 * diagnosis for the user in that case.
 * @param {{data: Uint8ClampedArray|number[], width: number, height: number}} imageData
 * @returns {{blurScore: number, glareRatio: number, isAcceptable: boolean, reason: string|null}}
 */
export function assessPhotoQuality(imageData) {
  const blurScore = computeBlurScore(imageData);
  const glareRatio = computeGlareRatio(imageData);

  if (glareRatio > GLARE_RATIO_THRESHOLD) {
    return {
      blurScore,
      glareRatio,
      isAcceptable: false,
      reason: "Too much glare — avoid direct light or flash reflecting off the invoice, then retake.",
    };
  }

  if (blurScore < BLUR_VARIANCE_THRESHOLD) {
    return {
      blurScore,
      glareRatio,
      isAcceptable: false,
      reason: "Photo looks blurry — hold the camera steady and let it focus, then retake.",
    };
  }

  return { blurScore, glareRatio, isAcceptable: true, reason: null };
}
