import type { Metadata, Viewport } from "next";
// Design tokens (mirror of @fbgroup/ui theme.ts) — must precede globals.css so
// the app's CSS can reference --space-*, --text-*, --motion-*, etc.
import "../../../../packages/ui/src/tokens.css";
import "./globals.css";
import "./ui-kit.css";

export const metadata: Metadata = {
  title: "FB Group F&B Platform",
  description: "Singapore F&B CRM & QR Ordering PoC",
  manifest: "/manifest.webmanifest",
  // Enables installable, chrome-less full-screen via iOS "Add to Home Screen" —
  // the proper home for a bottom tab bar (no Safari toolbar fighting it).
  appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "FB Group" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // viewport-fit=cover is REQUIRED for env(safe-area-inset-*) to be non-zero, so
  // the tab bar / sheets clear the notch and home indicator.
  viewportFit: "cover",
  themeColor: "#e23a0f",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
