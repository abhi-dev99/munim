/**
 * Haptic feedback for invoice scan results, wrapping navigator.vibrate().
 * Vibration support is inconsistent (iOS Safari has none at all), so every
 * call is feature-checked and wrapped — a missing or throwing vibrate() must
 * never break the scan-result UI.
 */

const SUCCESS_PATTERN = 40;
const WARNING_PATTERN = [40, 60, 40];
const ALERT_PATTERN = [50, 80, 50, 80, 50];

function vibrate(pattern) {
  if (typeof navigator === "undefined" || typeof navigator.vibrate !== "function") return;
  try {
    navigator.vibrate(pattern);
  } catch {
    // Some browsers throw instead of returning false when vibration is
    // blocked (e.g. no user-gesture in the current call stack).
  }
}

export function vibrateSuccess() {
  vibrate(SUCCESS_PATTERN);
}

export function vibrateWarning() {
  vibrate(WARNING_PATTERN);
}

export function vibrateAlert() {
  vibrate(ALERT_PATTERN);
}
