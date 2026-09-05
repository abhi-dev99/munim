import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { vibrateAlert, vibrateSuccess, vibrateWarning } from "./haptics.js";

let originalVibrate;

beforeEach(() => {
  originalVibrate = navigator.vibrate;
});

afterEach(() => {
  navigator.vibrate = originalVibrate;
});

describe("vibrateSuccess", () => {
  it("fires a single short pulse", () => {
    navigator.vibrate = vi.fn();
    vibrateSuccess();
    expect(navigator.vibrate).toHaveBeenCalledWith(40);
  });
});

describe("vibrateWarning", () => {
  it("fires a double-pulse pattern", () => {
    navigator.vibrate = vi.fn();
    vibrateWarning();
    expect(navigator.vibrate).toHaveBeenCalledWith([40, 60, 40]);
  });
});

describe("vibrateAlert", () => {
  it("fires a distinct triple-pulse pattern, longer than the warning pattern", () => {
    navigator.vibrate = vi.fn();
    vibrateAlert();
    expect(navigator.vibrate).toHaveBeenCalledWith([50, 80, 50, 80, 50]);
  });
});

describe("unsupported browsers", () => {
  it("does not throw when navigator.vibrate is undefined", () => {
    navigator.vibrate = undefined;
    expect(() => vibrateSuccess()).not.toThrow();
    expect(() => vibrateWarning()).not.toThrow();
    expect(() => vibrateAlert()).not.toThrow();
  });

  it("does not throw when navigator.vibrate itself throws", () => {
    navigator.vibrate = () => {
      throw new Error("vibration blocked");
    };
    expect(() => vibrateAlert()).not.toThrow();
  });
});
