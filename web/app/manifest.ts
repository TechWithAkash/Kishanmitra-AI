import type { MetadataRoute } from "next";

/** Lets farmers "Add to Home screen" on a phone and open KisanMitra like an app. */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "KisanMitra AI",
    short_name: "KisanMitra",
    description: "Farming help in your language: crop problems, mandi prices and weather, by text, voice or photo.",
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#16a34a",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }],
  };
}
