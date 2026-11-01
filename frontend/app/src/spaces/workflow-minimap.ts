import { NODE_HEIGHT, NODE_WIDTH, type Position } from './workflow-board';
import { screenToWorld, type WorkflowCamera } from './workflow-viewport';

interface MinimapRectangle extends Position {
  width: number;
  height: number;
}

export interface WorkflowMinimapProjection extends MinimapRectangle {
  scale: number;
  viewport: MinimapRectangle;
  nodes: MinimapRectangle[];
}

/** Include the visible world as well as every card, so panning never loses the viewport. */
export function workflowMinimap(
  nodes: readonly Position[],
  camera: WorkflowCamera,
  viewport: { width: number; height: number },
  size = { width: 200, height: 112 },
  padding = 10,
): WorkflowMinimapProjection {
  const width = Math.max(1, size.width);
  const height = Math.max(1, size.height);
  const start = screenToWorld({ x: 0, y: 0 }, camera);
  const end = screenToWorld(
    { x: Math.max(0, viewport.width), y: Math.max(0, viewport.height) },
    camera,
  );
  let left = start.x;
  let top = start.y;
  let right = end.x;
  let bottom = end.y;
  nodes.forEach((node) => {
    left = Math.min(left, node.x);
    top = Math.min(top, node.y);
    right = Math.max(right, node.x + NODE_WIDTH);
    bottom = Math.max(bottom, node.y + NODE_HEIGHT);
  });
  const inset = Math.max(0, Math.min(padding, (Math.min(width, height) - 1) / 2));
  const scale = Math.min(
    (width - inset * 2) / Math.max(1, right - left),
    (height - inset * 2) / Math.max(1, bottom - top),
  );
  const x = width / 2 - ((left + right) / 2) * scale;
  const y = height / 2 - ((top + bottom) / 2) * scale;
  return {
    x,
    y,
    width,
    height,
    scale,
    viewport: {
      x: start.x * scale + x,
      y: start.y * scale + y,
      width: (end.x - start.x) * scale,
      height: (end.y - start.y) * scale,
    },
    nodes: nodes.map((node) => ({
      x: node.x * scale + x,
      y: node.y * scale + y,
      width: NODE_WIDTH * scale,
      height: NODE_HEIGHT * scale,
    })),
  };
}

export function minimapToWorld(point: Position, projection: WorkflowMinimapProjection): Position {
  return {
    x: (point.x - projection.x) / projection.scale,
    y: (point.y - projection.y) / projection.scale,
  };
}
