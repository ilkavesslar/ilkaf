import type { CSSProperties } from "react";

export const STAGE_ASPECT = 16 / 9;

export type NormalizedBox = {
  xMin: number;
  yMin: number;
  xMax: number;
  yMax: number;
};

function percent(value: number): string {
  if (!Number.isFinite(value)) {
    return "0%";
  }
  const clamped = Math.min(100, Math.max(0, value * 100));
  const rounded = Math.round(clamped * 1000) / 1000;
  return `${rounded}%`;
}

export function mapNormalizedBox(
  box: NormalizedBox,
  imageWidth: number,
  imageHeight: number,
  stageAspect = STAGE_ASPECT,
): CSSProperties {
  let left = box.xMin;
  let top = box.yMin;
  let width = Math.max(0, box.xMax - box.xMin);
  let height = Math.max(0, box.yMax - box.yMin);
  if (imageWidth > 0 && imageHeight > 0 && stageAspect > 0) {
    const imageAspect = imageWidth / imageHeight;
    if (imageAspect > stageAspect) {
      const imageHeightFraction = stageAspect / imageAspect;
      const pad = (1 - imageHeightFraction) / 2;
      top = pad + box.yMin * imageHeightFraction;
      height = Math.max(0, box.yMax - box.yMin) * imageHeightFraction;
    } else if (imageAspect < stageAspect) {
      const imageWidthFraction = imageAspect / stageAspect;
      const pad = (1 - imageWidthFraction) / 2;
      left = pad + box.xMin * imageWidthFraction;
      width = Math.max(0, box.xMax - box.xMin) * imageWidthFraction;
    }
  }
  return {
    left: percent(left),
    top: percent(top),
    width: percent(width),
    height: percent(height),
  };
}
