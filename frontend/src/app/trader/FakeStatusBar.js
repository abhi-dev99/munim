"use client";

import { useEffect, useState } from "react";

/**
 * The trader shell used to hardcode a fake iOS status bar (literal "9:41" text
 * + three dots standing in for signal/wifi/battery) so the app looked
 * mobile-native when viewed in a desktop browser during development.
 *
 * Now that /trader is a real installable PWA, an installed instance runs
 * inside the OS's own chrome and already has a real status bar — stacking a
 * fake one on top of it would look broken, not native. So this renders only
 * when the app is NOT running in standalone/installed mode (i.e. still being
 * previewed inside an ordinary browser tab), where the fake bar is still a
 * handy visual aid.
 *
 * Defaults to hidden (assumes standalone) until the display-mode check runs,
 * so an installed app never flashes the fake bar even for a frame — the
 * small tradeoff is a brief absence of the bar in browser-preview mode on
 * first paint, which is a non-issue since that's a dev-only aid.
 */
export default function FakeStatusBar() {
  const [showFakeBar, setShowFakeBar] = useState(false);

  useEffect(() => {
    const standaloneQuery = window.matchMedia("(display-mode: standalone)");
    const isStandalone = () =>
      standaloneQuery.matches || window.navigator.standalone === true;

    const update = () => setShowFakeBar(!isStandalone());
    update();

    standaloneQuery.addEventListener("change", update);
    return () => standaloneQuery.removeEventListener("change", update);
  }, []);

  if (!showFakeBar) return null;

  return (
    <div className="h-6 w-full bg-black/5 flex items-center justify-between px-4">
      <span className="text-[10px] font-medium">9:41</span>
      <div className="flex gap-1">
        <div className="w-3 h-3 rounded-full bg-black/20"></div>
        <div className="w-3 h-3 rounded-full bg-black/20"></div>
        <div className="w-3 h-3 rounded-full bg-black/20"></div>
      </div>
    </div>
  );
}
