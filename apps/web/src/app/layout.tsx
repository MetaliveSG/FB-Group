import type { Metadata } from "next";
// Design tokens (mirror of @fbgroup/ui theme.ts) — must precede globals.css so
// the app's CSS can reference --space-*, --text-*, --motion-*, etc.
import "../../../../packages/ui/src/tokens.css";
import "./globals.css";
import "./ui-kit.css";

export const metadata: Metadata = {
  title: "FB Group F&B Platform",
  description: "Singapore F&B CRM & QR Ordering PoC",
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
