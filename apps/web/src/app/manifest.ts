import type { MetadataRoute } from "next";

// Web App Manifest → served at /manifest.webmanifest. Makes the customer app
// installable ("Add to Home Screen"), so it launches full-screen without Safari's
// toolbars — the correct experience for the bottom tab-bar layout.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "FB Group — QR Ordering & Rewards",
    short_name: "FB Group",
    description: "Scan, order, earn coins and play to win.",
    // iOS launches the URL it was added from; start_url is the web fallback.
    start_url: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#ffffff",
    theme_color: "#e23a0f",
  };
}
