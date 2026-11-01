import { NODE_HEIGHT, NODE_WIDTH, type Position } from './workflow-board';

export const MIN_ZOOM = 0.01;
export const MAX_ZOOM = 2;

/** World coordinates are scaled first, then translated in viewport CSS pixels. */
export interface WorkflowCamera {
  x: number;
  y: number;
  zoom: number;
}

export function screenToWorld(point: Position, camera: WorkflowCamera): Position {
  return {
    x: (point.x - camera.x) / camera.zoom,
    y: (point.y - camera.y) / camera.zoom,
  };
}

/** Keep the world point under the cursor stationary while changing magnification. */
export function zoomWorkflowAt(
  camera: WorkflowCamera,
  nextZoom: number,
  anchor: Position,
): WorkflowCamera {
  const zoom = Math.max(
    Math.min(MIN_ZOOM, camera.zoom),
    Math.min(MAX_ZOOM, Number.isFinite(nextZoom) ? nextZoom : camera.zoom),
  );
  if (zoom === camera.zoom) return camera;
  const point = screenToWorld(anchor, camera);
  return { x: anchor.x - point.x * zoom, y: anchor.y - point.y * zoom, zoom };
}

/** Fit all card bounds, including signed coordinates; may zoom out beyond the manual limit. */
export function fitWorkflow(
  nodes: readonly Position[],
  viewport: { width: number; height: number },
  padding = 48,
): WorkflowCamera {
  const width = Math.max(0, viewport.width);
  const height = Math.max(0, viewport.height);
  if (!nodes.length) return { x: width / 2, y: height / 2, zoom: 1 };
  const left = Math.min(...nodes.map((node) => node.x));
  const top = Math.min(...nodes.map((node) => node.y));
  const right = Math.max(...nodes.map((node) => node.x + NODE_WIDTH));
  const bottom = Math.max(...nodes.map((node) => node.y + NODE_HEIGHT));
  const inset = Math.max(0, padding);
  const zoom = Math.max(
    1e-6,
    Math.min(1, (width - inset * 2) / (right - left), (height - inset * 2) / (bottom - top)),
  );
  return {
    x: (width - (right - left) * zoom) / 2 - left * zoom,
    y: (height - (bottom - top) * zoom) / 2 - top * zoom,
    zoom,
  };
}
