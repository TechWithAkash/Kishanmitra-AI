/** Crops the photo check can recognise (ids match the backend). */
export const PHOTO_CROPS = [
  { value: "any", label: "Not sure" },
  { value: "tomato", label: "🍅 Tomato" },
  { value: "potato", label: "🥔 Potato" },
  { value: "maize", label: "🌽 Maize (corn)" },
  { value: "capsicum", label: "🫑 Pepper" },
] as const;
