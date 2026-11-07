import {
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent,
} from 'react';
import { Icon } from '../shared/Icon';
import type { ConfigurationData, ConfigurationGroup } from './ConfigurationPage';
import { useWorkflowCamera } from './useWorkflowCamera';
import WorkflowMinimap from './WorkflowMinimap';
import { configurationBadgeClass } from './configuration-appearance';
import {
  connectWorkflow,
  moveWorkflowNode,
  NODE_HEIGHT,
  NODE_WIDTH,
  transitionPath,
  workflowNodes,
  workflowIssues,
  type Position,
} from './workflow-board';

export default function WorkflowBoard({
  data,
  group,
  pending,
  onChange,
  onAdd,
  onEdit,
  actions,
  history,
}: {
  data: ConfigurationData;
  group: ConfigurationGroup;
  pending: boolean;
  onChange: (data: ConfigurationData) => void;
  onAdd: (position?: Position) => void;
  onEdit: (index: number) => void;
  actions: {
    dirty: boolean;
    statusText: string;
    saveDisabled?: boolean;
    cancelDisabled?: boolean;
    onSave: () => void;
    onCancel: () => void;
  };
  history: { canUndo: boolean; canRedo: boolean; onUndo: () => void; onRedo: () => void };
}) {
  const [selected, select] = useState('');
  const [connecting, connect] = useState('');
  const [selectedEdge, selectEdge] = useState<{ source: string; target: string } | null>(null);
  const [preview, setPreview] = useState<{ key: string; point: Position } | null>(null);
  const [notice, setNotice] = useState('');
  const viewport = useRef<HTMLDivElement>(null);
  const nodeButtons = useRef(new Map<string, HTMLButtonElement>());
  const previousForms = useRef(group.forms);
  const drag = useRef<{
    key: string;
    start: Position;
    point: Position;
    origin: Position;
    moved: boolean;
  } | null>(null);
  const suppressClick = useRef(false);
  const marker = useId().replace(/:/g, '');
  const savedNodes = workflowNodes(group);
  const nodes = savedNodes.map((node) =>
    preview?.key === node.key ? { ...node, ...preview.point } : node,
  );
  const source = nodes.find((node) => node.key === connecting);
  const initialKey = nodes.find((node) => node.stage === 'queue')?.key || nodes[0]?.key;
  const byKey = new Map(nodes.map((node) => [node.key, node]));
  const map = useWorkflowCamera(viewport, savedNodes, () => end(true));
  const zoom = map.camera.zoom;
  const edges = nodes.flatMap((node) =>
    node.transitions.flatMap((target) => {
      const destination = byKey.get(target);
      return !destination || node.key === target ? [] : [{ source: node, target: destination }];
    }),
  );
  const edge =
    selectedEdge &&
    edges.find(
      (item) => item.source.key === selectedEdge.source && item.target.key === selectedEdge.target,
    );
  const issues = workflowIssues(savedNodes);
  const targets = source
    ? nodes.filter((node) => node.key !== source.key && !source.transitions.includes(node.key))
    : [];
  useLayoutEffect(() => {
    const oldKeys = new Set(
      workflowNodes({ ...group, forms: previousForms.current }).map((node) => node.key),
    );
    previousForms.current = group.forms;
    const added = nodes.find((node) => !oldKeys.has(node.key));
    if (added) focusNode(added.key);
  }, [group]);

  function resetSelection() {
    select('');
    selectEdge(null);
    connect('');
    requestAnimationFrame(() => viewport.current?.focus({ preventScroll: true }));
  }
  function focusNode(key: string) {
    select(key);
    selectEdge(null);
    requestAnimationFrame(() => nodeButtons.current.get(key)?.focus({ preventScroll: true }));
    const node = byKey.get(key);
    if (node) map.centerOn(node);
  }
  function addAtCenter() {
    const point = map.centerWorld();
    onAdd({ x: point.x - NODE_WIDTH / 2, y: point.y - NODE_HEIGHT / 2 });
  }

  function addConnection(target: string) {
    if (!source || source.key === target || pending) return;
    if (source.transitions.includes(target)) {
      setNotice('To przejście już istnieje. Wybierz inny etap.');
      return;
    }
    onChange(connectWorkflow(data, source.key, target));
    setNotice(`Dodano przejście: ${source.label} → ${byKey.get(target)?.label}.`);
    finishConnecting();
  }
  function choose(key: string) {
    if (suppressClick.current) {
      suppressClick.current = false;
      return;
    }
    if (source) {
      addConnection(key);
      return;
    }
    select(key);
    selectEdge(null);
  }
  function beginConnection(key: string) {
    if (connecting === key) {
      finishConnecting();
      return;
    }
    select(key);
    selectEdge(null);
    connect(key);
    setNotice('');
    requestAnimationFrame(() => viewport.current?.focus({ preventScroll: true }));
  }
  function finishConnecting() {
    connect('');
    if (source)
      requestAnimationFrame(() =>
        nodeButtons.current.get(source.key)?.focus({ preventScroll: true }),
      );
  }
  function start(event: PointerEvent<HTMLButtonElement>, key: string) {
    suppressClick.current = false;
    if (pending || source || event.button !== 0) return;
    const node = byKey.get(key)!;
    drag.current = {
      key,
      start: node,
      point: node,
      origin: map.worldPoint(event),
      moved: false,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
    select(key);
    selectEdge(null);
  }
  function move(event: PointerEvent<HTMLButtonElement>) {
    const active = drag.current;
    if (!active || pending) return;
    const location = map.worldPoint(event);
    const dx = location.x - active.origin.x,
      dy = location.y - active.origin.y;
    if (!active.moved && Math.abs(dx) + Math.abs(dy) < 4) return;
    active.moved = true;
    active.point = {
      x: Math.max(-1000000, Math.min(1000000, active.start.x + dx)),
      y: Math.max(-1000000, Math.min(1000000, active.start.y + dy)),
    };
    setPreview({ key: active.key, point: active.point });
  }
  function end(cancelled = false) {
    const active = drag.current;
    drag.current = null;
    setPreview(null);
    if (active?.moved) {
      suppressClick.current = true;
      if (!cancelled && !pending) onChange(moveWorkflowNode(data, active.key, active.point));
    }
  }
  function undo(redo = false) {
    if (pending || (redo ? !history.canRedo : !history.canUndo)) return;
    end(true);
    connect('');
    selectEdge(null);
    (redo ? history.onRedo : history.onUndo)();
    setNotice(redo ? 'Ponowiono zmianę.' : 'Cofnięto zmianę.');
  }
  return (
    <div
      className="work-flow-shell"
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          finishConnecting();
          end(true);
        }
        if (
          (event.ctrlKey || event.metaKey) &&
          !event.altKey &&
          !(event.target as HTMLElement).closest(
            'input, textarea, select, [contenteditable="true"]',
          )
        ) {
          if (event.key.toLowerCase() === 'z' || event.key.toLowerCase() === 'y') {
            event.preventDefault();
            undo(event.shiftKey || event.key.toLowerCase() === 'y');
          }
        }
      }}
    >
      <div className="tasks-filterbar tasks-filterbar--directory workplace-edit-modal__team-toolbar member-access-toolbar work-flow-toolbar app-toolbar app-toolbar--embedded">
        <div
          className="work-flow-history app-toolbar__controls"
          role="group"
          aria-label="Historia zmian procesu"
        >
          <button
            type="button"
            className="tasks-filter-button work-flow-icon-button"
            disabled={pending || !history.canUndo}
            onClick={() => undo()}
            title="Cofnij (Ctrl / ⌘ + Z)"
            aria-label="Cofnij zmianę"
          >
            <Icon name="rotate-ccw" />
          </button>
          <button
            type="button"
            className="tasks-filter-button work-flow-icon-button"
            disabled={pending || !history.canRedo}
            onClick={() => undo(true)}
            title="Ponów (Ctrl / ⌘ + Shift + Z)"
            aria-label="Ponów zmianę"
          >
            <span className="work-flow-redo">
              <Icon name="rotate-ccw" />
            </span>
          </button>
        </div>
        <span className={`work-flow-save-state${actions.dirty ? ' is-dirty' : ''}`} role="status">
          {actions.statusText}
        </span>
        <div className="member-access-save-actions app-toolbar__actions">
          <button
            type="button"
            className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
            disabled={pending || !actions.dirty || actions.saveDisabled}
            onClick={() => {
              setNotice('');
              connect('');
              actions.onSave();
            }}
          >
            <Icon name="check" />
            Zapisz
          </button>
          <button
            type="button"
            className="tasks-filter-button"
            disabled={pending || actions.cancelDisabled || !actions.dirty}
            onClick={() => {
              resetSelection();
              setNotice('');
              actions.onCancel();
            }}
          >
            Anuluj
          </button>
        </div>
      </div>
      {data.shared ? (
        <p className="work-flow-shared">
          <Icon name="info" />
          Wspólny proces · zapis zmieni konfigurację w {data.spaces_count} przestrzeniach.
        </p>
      ) : null}
      <div className="u-sr-only" role="status">
        {notice ||
          (source
            ? `Łączenie z „${source.label}”. Wybierz etap na mapie. Escape anuluje łączenie.`
            : '')}
      </div>
      <div className="work-flow-editor">
        <div className="work-flow-workspace">
          <div
            className={`work-flow-viewport${map.panning ? ' is-panning' : ''}${map.hand ? ' is-hand' : ''}`}
            {...map.handlers}
            style={{
              backgroundPosition: `${map.camera.x}px ${map.camera.y}px`,
              backgroundSize: `${Math.max(8, 20 * zoom)}px ${Math.max(8, 20 * zoom)}px`,
            }}
            ref={viewport}
            role="region"
            aria-label="Tablica procesu pracy"
            tabIndex={0}
          >
            {nodes.length ? (
              <div
                className="work-flow-canvas"
                style={{
                  transform: `translate(${map.camera.x}px, ${map.camera.y}px) scale(${zoom})`,
                }}
              >
                <svg className="work-flow-connections" width={1} height={1} aria-hidden="true">
                  <defs>
                    {['arrow', 'active-arrow'].map((name) => (
                      <marker
                        key={name}
                        id={`${marker}-${name}`}
                        viewBox="0 0 10 10"
                        refX="9"
                        refY="5"
                        markerWidth="7"
                        markerHeight="7"
                        orient="auto-start-reverse"
                      >
                        <path d="M 0 0 L 10 5 L 0 10 z" />
                      </marker>
                    ))}
                  </defs>
                  {edges.map(({ source: from, target: to }, index) => {
                    const active = edge
                      ? edge.source.key === from.key && edge.target.key === to.key
                      : from.key === selected || to.key === selected;
                    const path = transitionPath(from, to, index);
                    return (
                      <g key={`${from.key}:${to.key}`}>
                        <path
                          className={`work-flow-edge${active ? ' is-selected' : selected || edge ? ' is-muted' : ''}`}
                          d={path}
                          markerEnd={`url(#${marker}-${active ? 'active-arrow' : 'arrow'})`}
                        />
                        <path
                          className="work-flow-edge-hit"
                          d={path}
                          onClick={() => {
                            if (!pending && !source) {
                              selectEdge({ source: from.key, target: to.key });
                              select('');
                            }
                          }}
                        >
                          <title>
                            {from.label} → {to.label}
                          </title>
                        </path>
                      </g>
                    );
                  })}
                </svg>
                {nodes.map((node) => (
                  <div
                    className="work-flow-node-wrap"
                    key={node.key}
                    style={{ left: node.x, top: node.y, width: NODE_WIDTH, height: NODE_HEIGHT }}
                    onFocusCapture={(event) => {
                      if (!drag.current && event.target.matches(':focus-visible')) map.reveal(node);
                    }}
                  >
                    <button
                      type="button"
                      ref={(element) => {
                        if (element) nodeButtons.current.set(node.key, element);
                        else nodeButtons.current.delete(node.key);
                      }}
                      className={`work-flow-node${selected === node.key ? ' is-selected' : ''}${source && targets.some((target) => target.key === node.key) ? ' is-target' : ''}${source && source.key !== node.key && !targets.some((target) => target.key === node.key) ? ' is-unavailable' : ''}`}
                      aria-label={`Etap: ${node.label}`}
                      aria-pressed={selected === node.key}
                      disabled={pending}
                      onClick={() => choose(node.key)}
                      onDoubleClick={() => {
                        if (!pending && !source) onEdit(node.index);
                      }}
                      onPointerDown={(event) => start(event, node.key)}
                      onPointerMove={move}
                      onPointerUp={() => end()}
                      onPointerCancel={() => end(true)}
                      onLostPointerCapture={() => {
                        if (drag.current) end(true);
                      }}
                      onKeyDown={(event) => {
                        if (!pending && !source && event.key === 'Enter') {
                          event.preventDefault();
                          onEdit(node.index);
                          return;
                        }
                        if (
                          pending ||
                          source ||
                          !event.altKey ||
                          !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)
                        )
                          return;
                        event.preventDefault();
                        const step = event.shiftKey ? 40 : 10;
                        const point = {
                          x:
                            node.x +
                            (event.key === 'ArrowRight'
                              ? step
                              : event.key === 'ArrowLeft'
                                ? -step
                                : 0),
                          y:
                            node.y +
                            (event.key === 'ArrowDown'
                              ? step
                              : event.key === 'ArrowUp'
                                ? -step
                                : 0),
                        };
                        onChange(moveWorkflowNode(data, node.key, point));
                        map.reveal(point);
                      }}
                      title={`${node.label}. Przeciągnij lub użyj Alt + strzałek. Kliknij dwukrotnie lub naciśnij Enter, aby edytować.`}
                    >
                      <span
                        className={`work-flow-node-label ${configurationBadgeClass}`}
                        style={{ '--tag-color': node.color } as CSSProperties}
                      >
                        {node.icon ? (
                          <span className="tasks-issue-type" aria-hidden="true">
                            <Icon name={node.icon} />
                          </span>
                        ) : (
                          <span
                            className={`status-indicator status-${node.category}`}
                            aria-hidden="true"
                          />
                        )}
                        <span>{node.label}</span>
                      </span>
                      <span className="work-flow-node-meta">
                        {node.stageLabel}
                        {node.limit ? ` · Limit: ${node.limit}` : ''}
                      </span>
                      {node.key === initialKey ? (
                        <span className="work-flow-node-start">Początek procesu</span>
                      ) : null}
                      {issues.some((issue) => issue.key === node.key) ? (
                        <span className="work-flow-node-warning" title="Etap wymaga sprawdzenia">
                          <Icon name="alert-triangle" />
                        </span>
                      ) : null}
                    </button>
                    <button
                      type="button"
                      className="work-flow-port"
                      disabled={pending || nodes.length < 2}
                      onClick={() => beginConnection(node.key)}
                      aria-label={`${connecting === node.key ? 'Anuluj łączenie z' : 'Dodaj przejście z'}: ${node.label}`}
                      aria-pressed={connecting === node.key}
                      title={connecting === node.key ? 'Anuluj łączenie' : 'Dodaj przejście'}
                    >
                      <Icon name="plus" />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="work-flow-empty">
                <Icon name="workflow" />
                <p>Dodaj pierwszy etap procesu</p>
                <p>Potem połącz etapy w ścieżkę od kolejki do zakończenia.</p>
                <button
                  type="button"
                  className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
                  disabled={pending}
                  onClick={addAtCenter}
                >
                  <Icon name="plus" />
                  Dodaj pierwszy etap
                </button>
              </div>
            )}
          </div>
          {nodes.length > 0 ? (
            <WorkflowMinimap
              nodes={nodes}
              selected={selected}
              camera={map.camera}
              viewportSize={map.viewportSize}
              onPanTo={(point) => {
                end(true);
                map.panTo(point);
              }}
              onZoom={map.zoomTo}
              onFit={map.fit}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}
