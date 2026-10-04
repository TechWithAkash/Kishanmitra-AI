export type PreparedImage = {
  /** JPEG to upload (long side ≤ 1024 px: small, fast, and enough for the model). */
  blob: Blob;
  /** Tiny preview that is safe to keep in localStorage chat history. */
  thumb: string;
  /** Object URL for the full preview in the composer. Revoke it when done. */
  previewUrl: string;
};

const MAX_UPLOAD_BYTES = 12 * 1024 * 1024;

function drawScaled(bitmap: ImageBitmap, maxSide: number): HTMLCanvasElement {
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d")!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  return canvas;
}

const toBlob = (canvas: HTMLCanvasElement, quality: number) =>
  new Promise<Blob>((resolve, reject) =>
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Could not process the image"))), "image/jpeg", quality),
  );

/** Validates, fixes orientation (EXIF), downsizes and re-encodes a photo from the camera or gallery. */
export async function prepareImage(file: Blob): Promise<PreparedImage> {
  if (file.type && !file.type.startsWith("image/")) throw new Error("Please choose an image file.");
  if (file.size > MAX_UPLOAD_BYTES * 2) throw new Error("That image is too large. Please choose one under 20 MB.");

  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
  } catch {
    throw new Error("I could not read that image. Try a JPG or PNG photo.");
  }
  try {
    const blob = await toBlob(drawScaled(bitmap, 1024), 0.85);
    const thumb = drawScaled(bitmap, 256).toDataURL("image/jpeg", 0.7);
    return { blob, thumb, previewUrl: URL.createObjectURL(blob) };
  } finally {
    bitmap.close();
  }
}
