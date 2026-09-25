/**
 * Canvas-side of the image editor: turns the crop/rotation/flip chosen in
 * the UI into an actual JPEG blob, entirely in the browser (no server
 * round-trip, no paid image API).
 */

export interface CropArea {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ImageTransform {
  crop: CropArea;
  rotation: number; // degrees, multiples of 90
  flipHorizontal?: boolean;
  flipVertical?: boolean;
}

export const ASPECT_PRESETS = [
  { label: "Libre", value: undefined },
  { label: "1:1", value: 1 },
  { label: "4:3", value: 4 / 3 },
  { label: "16:9", value: 16 / 9 },
] as const;

/** Largest edge of the exported image — keeps uploads reasonable. */
const MAX_EXPORT_EDGE = 1600;
const EXPORT_QUALITY = 0.85;

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.addEventListener("load", () => resolve(image));
    image.addEventListener("error", () => reject(new Error("image-load-failed")));
    // Needed when the source is served from the API origin.
    image.crossOrigin = "anonymous";
    image.src = src;
  });
}

/**
 * Applies rotation/flip first (on a full-size canvas), then extracts the
 * crop rectangle, which is expressed in the *rotated* image's coordinates —
 * that is what react-easy-crop reports.
 */
export async function renderEditedImage(
  src: string,
  transform: ImageTransform,
  fileName = "image.jpg"
): Promise<File> {
  const image = await loadImage(src);
  const { crop, rotation, flipHorizontal, flipVertical } = transform;
  const radians = (rotation * Math.PI) / 180;

  const rotatedWidth =
    Math.abs(Math.cos(radians) * image.width) + Math.abs(Math.sin(radians) * image.height);
  const rotatedHeight =
    Math.abs(Math.sin(radians) * image.width) + Math.abs(Math.cos(radians) * image.height);

  const stage = document.createElement("canvas");
  stage.width = Math.round(rotatedWidth);
  stage.height = Math.round(rotatedHeight);
  const stageCtx = stage.getContext("2d");
  if (!stageCtx) throw new Error("canvas-unavailable");

  stageCtx.translate(stage.width / 2, stage.height / 2);
  stageCtx.rotate(radians);
  stageCtx.scale(flipHorizontal ? -1 : 1, flipVertical ? -1 : 1);
  stageCtx.drawImage(image, -image.width / 2, -image.height / 2);

  const output = document.createElement("canvas");
  const scale = Math.min(1, MAX_EXPORT_EDGE / Math.max(crop.width, crop.height));
  output.width = Math.max(1, Math.round(crop.width * scale));
  output.height = Math.max(1, Math.round(crop.height * scale));
  const outputCtx = output.getContext("2d");
  if (!outputCtx) throw new Error("canvas-unavailable");

  outputCtx.drawImage(
    stage,
    crop.x, crop.y, crop.width, crop.height,
    0, 0, output.width, output.height
  );

  const blob = await new Promise<Blob | null>((resolve) =>
    output.toBlob(resolve, "image/jpeg", EXPORT_QUALITY)
  );
  if (!blob) throw new Error("export-failed");

  const safeName = fileName.replace(/\.[^.]+$/, "") + ".jpg";
  return new File([blob], safeName, { type: "image/jpeg" });
}
