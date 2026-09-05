import FakeStatusBar from "./FakeStatusBar";
import ServiceWorkerRegister from "./ServiceWorkerRegister";

// /trader is the trader-facing PWA entry point (see frontend/public/manifest.json,
// whose start_url/scope both point here). This metadata is what makes an
// installed instance show the right name/icon on the home screen and status
// bar color, and is what a browser's installability check inspects.
export const metadata = {
  manifest: "/manifest.json",
  applicationName: "Munim.ai",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Munim.ai",
  },
  icons: {
    icon: [
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: "/icons/apple-touch-icon.png",
  },
};

export const viewport = {
  themeColor: "#0F172A",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function TraderLayout({ children }) {
  return (
    <div className="max-w-md mx-auto min-h-screen bg-[var(--bg-primary)] shadow-2xl overflow-hidden relative">
      <ServiceWorkerRegister />
      <FakeStatusBar />
      {children}
    </div>
  );
}
