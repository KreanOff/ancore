export interface BannerCrop {
  x: number;
  y: number;
  zoom: number;
}

export interface BannerSize {
  width: number;
  height: number;
}

export const DEFAULT_BANNER_CROP: BannerCrop = { x: 50, y: 50, zoom: 1 };
export const MIN_BANNER_ZOOM = 1;
export const MAX_BANNER_ZOOM = 3;

function bounded(value: number | undefined, fallback: number, min: number, max: number) {
  return typeof value === 'number' && Number.isFinite(value)
    ? Math.min(max, Math.max(min, value))
    : fallback;
}

export function normalizeBannerCrop(crop: Partial<BannerCrop>): BannerCrop {
  return {
    x: bounded(crop.x, 50, 0, 100),
    y: bounded(crop.y, 50, 0, 100),
    zoom: bounded(crop.zoom, 1, MIN_BANNER_ZOOM, MAX_BANNER_ZOOM),
  };
}

export function sameBannerCrop(first: BannerCrop, second: BannerCrop) {
  return first.x === second.x && first.y === second.y && first.zoom === second.zoom;
}

export function bannerCropFromFields(
  fields: { name: string; value: unknown }[],
  fallback: BannerCrop,
): BannerCrop {
  const value = (name: keyof BannerCrop) => {
    const raw = fields.find((field) => field.name === 'profile_banner_' + name)?.value;
    const number =
      typeof raw === 'number' || (typeof raw === 'string' && raw.trim()) ? Number(raw) : Number.NaN;
    return Number.isFinite(number) ? number : fallback[name];
  };
  return normalizeBannerCrop({ x: value('x'), y: value('y'), zoom: value('zoom') });
}

export function bannerCropStyle(value: BannerCrop) {
  const crop = normalizeBannerCrop(value);
  const position = `${crop.x}% ${crop.y}%`;
  return {
    objectPosition: position,
    transform: `scale(${crop.zoom})`,
    transformOrigin: position,
  };
}

export function bannerOverflow(image: BannerSize, stage: BannerSize, zoom: number): BannerSize {
  if (
    ![image.width, image.height, stage.width, stage.height].every(
      (n) => Number.isFinite(n) && n > 0,
    )
  )
    return { width: 0, height: 0 };
  const scale = Math.max(stage.width / image.width, stage.height / image.height);
  const boundedZoom = normalizeBannerCrop({ zoom }).zoom;
  return {
    width: Math.max(0, image.width * scale * boundedZoom - stage.width),
    height: Math.max(0, image.height * scale * boundedZoom - stage.height),
  };
}

// Stage sizes and pointer deltas are both viewport pixels, including CSS/browser zoom.
export function moveBannerCrop(
  value: BannerCrop,
  image: BannerSize,
  stage: BannerSize,
  dx: number,
  dy: number,
): BannerCrop {
  const crop = normalizeBannerCrop(value);
  const overflow = bannerOverflow(image, stage, crop.zoom);
  return normalizeBannerCrop({
    ...crop,
    x:
      overflow.width > 0.001 && Number.isFinite(dx) ? crop.x - (dx / overflow.width) * 100 : crop.x,
    y:
      overflow.height > 0.001 && Number.isFinite(dy)
        ? crop.y - (dy / overflow.height) * 100
        : crop.y,
  });
}
