import { statusColorStyle } from '../shared/status-color';
import { useEffect, useRef, useState, type PointerEvent } from 'react';
import { Icon } from '../shared/Icon';
import {
  NODE_HEIGHT,
  NODE_WIDTH,
  transitionPath,
  type Position,
  type WorkflowNode,
} from './workflow-board';
import {
  minimapToWorld,
  workflowMinimap,
  type WorkflowMinimapProjection,
} from './workflow-minimap';
import { MAX_ZOOM, MIN_ZOOM, screenToWorld, type WorkflowCamera } from './workflow-viewport';

export default function WorkflowMinimap({
  nodes,
  selected,
  camera,
  viewportSize,
  onPanTo,
  onZoom,
  onFit,
}: {
  nodes: readonly WorkflowNode[];
  selected: string;
  camera: WorkflowCamera;
  viewportSize: { width: number; height: number };
  onPanTo: (point: Position) => void;
  onZoom: (zoom: number) => void;
  onFit: () => void;
}) {
  const drag = useRef<{
    id: number;
    projection: WorkflowMinimapProjection;
    original: Position;
    offset: Position;
    start: Position;
    moved: boolean;
  } | null>(null);
  const [dragging, setDragging] = useState(false);
  const pan = useRef(onPanTo);
  pan.current = onPanTo;
  const projection = drag.current?.projection || workflowMinimap(nodes, camera, viewportSize);
  const origin = screenToWorld({ x: 0, y: 0 }, camera);
  const visible = {
    x: origin.x * projection.scale + projection.x,
    y: origin.y * projection.scale + projection.y,
    width: (viewportSize.width / camera.zoom) * projection.scale,
    height: (viewportSize.height / camera.zoom) * projection.scale,
  };
  const byKey = new Map(nodes.map((node) => [node.key, node]));
  const edges = nodes.flatMap((node) =>
    node.transitions.flatMap((key) => {
      const target = byKey.get(key);
      return target && target !== node ? [{ source: node, target }] : [];
    }),
  );
  const zoomLabel = camera.zoom < MIN_ZOOM ? 'Mniej niż 1%' : `${Math.round(camera.zoom * 100)}%`;

  function center() {
    return screenToWorld({ x: viewportSize.width / 2, y: viewportSize.height / 2 }, camera);
  }
  function point(event: PointerEvent<HTMLButtonElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    return {
      x: ((event.clientX - rect.left) / rect.width) * projection.width,
      y: ((event.clientY - rect.top) / rect.height) * projection.height,
    };
  }
  function cancel() {
    const active = drag.current;
    if (!active) return;
    drag.current = null;
    setDragging(false);
    pan.current(active.original);
  }
  useEffect(() => {
    window.addEventListener('blur', cancel);
    return () => window.removeEventListener('blur', cancel);
  }, []);

  return (
    <div className="work-flow-minimap" role="group" aria-label="Minimapa procesu">
      <button
        type="button"
        className={`work-flow-minimap-map${dragging ? ' is-dragging' : ''}`}
        aria-label="Przesuń widok na minimapie"
        title="Kliknij lub przeciągnij, aby przesunąć widok. Strzałki przesuwają, Enter dopasowuje mapę."
        onPointerDown={(event) => {
          if (event.button !== 0 || drag.current) return;
          event.preventDefault();
          event.currentTarget.focus({ preventScroll: true });
          const location = point(event);
          const world = minimapToWorld(location, projection);
          const original = center();
          const inside =
            location.x >= visible.x &&
            location.x <= visible.x + visible.width &&
            location.y >= visible.y &&
            location.y <= visible.y + visible.height;
          drag.current = {
            id: event.pointerId,
            projection,
            original,
            start: location,
            moved: false,
            offset: inside ? { x: world.x - original.x, y: world.y - original.y } : { x: 0, y: 0 },
          };
          event.currentTarget.setPointerCapture(event.pointerId);
          setDragging(true);
          if (!inside) onPanTo(world);
        }}
        onPointerMove={(event) => {
          const active = drag.current;
          if (!active || active.id !== event.pointerId) return;
          const location = point(event);
          if (
            !active.moved &&
            Math.hypot(location.x - active.start.x, location.y - active.start.y) < 2
          )
            return;
          active.moved = true;
          const world = minimapToWorld(location, active.projection);
          onPanTo({ x: world.x - active.offset.x, y: world.y - active.offset.y });
        }}
        onPointerUp={(event) => {
          if (drag.current?.id !== event.pointerId) return;
          if (!drag.current.moved) onPanTo(minimapToWorld(point(event), drag.current.projection));
          drag.current = null;
          setDragging(false);
        }}
        onPointerCancel={cancel}
        onLostPointerCapture={cancel}
        onClick={(event) => {
          if (event.detail === 0) onFit();
        }}
        onKeyDown={(event) => {
          if (event.key === 'Escape' && drag.current) {
            event.stopPropagation();
            cancel();
          }
          if (drag.current || event.ctrlKey || event.metaKey || event.altKey) return;
          if (event.key === 'Home') {
            event.preventDefault();
            onFit();
          } else if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) {
            event.preventDefault();
            const middle = center();
            const step = event.shiftKey ? 0.6 : 0.2;
            onPanTo({
              x:
                middle.x +
                (viewportSize.width / camera.zoom) *
                  step *
                  (event.key === 'ArrowLeft' ? -1 : event.key === 'ArrowRight' ? 1 : 0),
              y:
                middle.y +
                (viewportSize.height / camera.zoom) *
                  step *
                  (event.key === 'ArrowUp' ? -1 : event.key === 'ArrowDown' ? 1 : 0),
            });
          }
        }}
      >
        <svg viewBox={`0 0 ${projection.width} ${projection.height}`} aria-hidden="true">
          <g transform={`translate(${projection.x} ${projection.y}) scale(${projection.scale})`}>
            {edges.map(({ source, target }, index) => (
              <path
                key={`${source.key}:${target.key}`}
                className="work-flow-minimap-edge"
                d={transitionPath(source, target, index)}
                vectorEffect="non-scaling-stroke"
              />
            ))}
            {nodes.map((node) => (
              <rect
                key={node.key}
                className={`work-flow-minimap-node status-${node.category}${selected === node.key ? ' is-selected' : ''}`}
                style={statusColorStyle(node.color)}
                x={node.x}
                y={node.y}
                width={NODE_WIDTH}
                height={NODE_HEIGHT}
                rx={6}
                vectorEffect="non-scaling-stroke"
              />
            ))}
          </g>
          <rect className="work-flow-minimap-view" {...visible} />
        </svg>
      </button>
      <div className="work-flow-minimap-zoom" role="group" aria-label="Skala mapy">
        <button
          type="button"
          className="tasks-filter-button work-flow-icon-button"
          disabled={dragging || camera.zoom <= MIN_ZOOM}
          aria-label="Pomniejsz mapę"
          title="Pomniejsz mapę"
          onClick={() => onZoom(camera.zoom * 0.8)}
        >
          <Icon name="minus" />
        </button>
        <input
          type="range"
          min={Math.min(MIN_ZOOM, camera.zoom) * 100}
          max={MAX_ZOOM * 100}
          step="any"
          value={camera.zoom * 100}
          disabled={dragging}
          aria-label="Powiększenie mapy"
          aria-valuetext={zoomLabel}
          title={zoomLabel}
          onChange={(event) => onZoom(Number(event.target.value) / 100)}
        />
        <button
          type="button"
          className="tasks-filter-button work-flow-icon-button"
          disabled={dragging || camera.zoom >= MAX_ZOOM}
          aria-label="Powiększ mapę"
          title="Powiększ mapę"
          onClick={() => onZoom(camera.zoom * 1.25)}
        >
          <Icon name="plus" />
        </button>
      </div>
    </div>
  );
}
