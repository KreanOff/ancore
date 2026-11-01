import { useId, useLayoutEffect, useRef, useState, type PointerEvent } from 'react';
import { Icon } from '../shared/Icon';
import type { ConfigurationData, ConfigurationGroup } from './ConfigurationPage';
import {
  arrangeWorkflow,
  connectWorkflow,
  moveWorkflowNode,
  NODE_HEIGHT,
  NODE_WIDTH,
  transitionPath,
  workflowNodes,
  type Position,
} from './workflow-board';

export default function WorkflowBoard({
  data,
  group,
  pending,
  onChange,
  onAdd,
  onEdit,
  onRemove,
  onMove,
  actions,
}: {
  data: ConfigurationData;
  group: ConfigurationGroup;
  pending: boolean;
  onChange: (data: ConfigurationData) => void;
  onAdd: () => void;
  onEdit: (index: number) => void;
  onRemove: (indices: number[]) => void;
  onMove: (index: number, direction: -1 | 1) => void;
  actions: {
    dirty: boolean;
    saveDisabled?: boolean;
    cancelDisabled?: boolean;
    onSave: () => void;
    onCancel: () => void;
  };
}) {
  const [selected, select] = useState('');
  const [connecting, connect] = useState('');
  const [zoom, setZoom] = useState(1);
  const [preview, setPreview] = useState<{ key: string; point: Position } | null>(null);
  const [notice, setNotice] = useState('');
  const viewport = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLDivElement>(null);
  const drag = useRef<{
    key: string;
    start: Position;
    point: Position;
    client: Position;
    scale: number;
    moved: boolean;
  } | null>(null);
  const suppressClick = useRef(false);
  const marker = useId().replace(/:/g, '');
  const nodes = workflowNodes(group).map((node) =>
    preview?.key === node.key ? { ...node, ...preview.point } : node,
  );
  const current = nodes.find((node) => node.key === selected);
  const initialKey = nodes.find((node) => node.stage === 'queue')?.key || nodes[0]?.key;
  const byKey = new Map(nodes.map((node) => [node.key, node]));
  const width = Math.max(760, ...nodes.map((node) => node.x + NODE_WIDTH + 48));
  const height = Math.max(420, ...nodes.map((node) => node.y + NODE_HEIGHT + 64));
  const edges = nodes.flatMap((node) =>
    node.transitions.flatMap((target) => {
      const destination = byKey.get(target);
      return !destination || node.key === target ? [] : [{ source: node, target: destination }];
    }),
  );
  const max = Number(
    group.management.fields.find((field) => field.name.endsWith('-MAX_NUM_FORMS'))?.value || 30,
  );

  useLayoutEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const observer = new ResizeObserver(() => {
      if (!element.clientWidth) return;
      setZoom(Math.max(0.5, Math.min(1, (element.clientWidth - 24) / width)));
      observer.disconnect();
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  function choose(key: string) {
    if (suppressClick.current) {
      suppressClick.current = false;
      return;
    }
    if (connecting && connecting !== key && !pending) {
      onChange(connectWorkflow(data, connecting, key));
      setNotice(
        `Dodano przejście: ${byKey.get(connecting)?.label} → ${byKey.get(key)?.label}. Zapisz proces, aby je zastosować.`,
      );
      connect('');
    } else select(key);
  }
  function start(event: PointerEvent<HTMLButtonElement>, key: string) {
    if (pending || connecting || event.button !== 0) return;
    const node = byKey.get(key)!;
    const scale = canvas.current
      ? canvas.current.getBoundingClientRect().width / canvas.current.offsetWidth
      : zoom;
    drag.current = {
      key,
      start: node,
      point: node,
      client: { x: event.clientX, y: event.clientY },
      scale,
      moved: false,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
    select(key);
  }
  function move(event: PointerEvent<HTMLButtonElement>) {
    const active = drag.current;
    if (!active || pending) return;
    const dx = (event.clientX - active.client.x) / active.scale;
    const dy = (event.clientY - active.client.y) / active.scale;
    if (!active.moved && Math.abs(dx) + Math.abs(dy) < 4) return;
    active.moved = true;
    active.point = {
      x: Math.max(0, Math.min(20000, active.start.x + dx)),
      y: Math.max(0, Math.min(20000, active.start.y + dy)),
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
  function fit() {
    if (!viewport.current) return;
    setZoom(Math.max(0.5, Math.min(1, (viewport.current.clientWidth - 24) / width)));
    viewport.current.scrollTo({ top: 0, left: 0 });
  }
  return (
    <>
      <div className="tasks-filterbar tasks-filterbar--directory workplace-edit-modal__team-toolbar member-access-toolbar work-flow-toolbar">
        <button
          type="button"
          className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
          disabled={pending || nodes.length >= max}
          onClick={onAdd}
          aria-haspopup="dialog"
        >
          <Icon name="plus" />
          Dodaj etap
        </button>
        <button
          type="button"
          className="tasks-filter-button"
          disabled={pending || !current}
          onClick={() => current && onEdit(current.index)}
          aria-haspopup="dialog"
        >
          <Icon name="pencil" />
          Edytuj
        </button>
        <button
          type="button"
          className="tasks-filter-button"
          disabled={pending || !current}
          onClick={() => {
            if (current) {
              onRemove([current.index]);
              select('');
              connect('');
            }
          }}
        >
          <Icon name="trash-2" />
          Usuń
        </button>
        <button
          type="button"
          className="tasks-filter-button"
          disabled={pending || !current || nodes.length < 2}
          aria-pressed={!!connecting}
          onClick={() => connect(connecting ? '' : selected)}
        >
          <Icon name="arrow-right" />
          {connecting ? 'Anuluj łączenie' : 'Dodaj przejście'}
        </button>
        <div className="member-access-save-actions">
          <button
            type="button"
            className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
            disabled={pending || !actions.dirty || actions.saveDisabled}
            onClick={actions.onSave}
          >
            <Icon name="check" />
            {pending ? 'Zapisywanie…' : 'Zapisz'}
          </button>
          <button
            type="button"
            className="tasks-filter-button"
            disabled={pending || actions.cancelDisabled || !actions.dirty}
            onClick={() => {
              connect('');
              setNotice('');
              actions.onCancel();
            }}
          >
            Anuluj
          </button>
        </div>
      </div>
      <div
        className="work-flow-editor"
        onKeyDown={(event) => {
          if (event.key === 'Escape') {
            connect('');
            end(true);
          }
        }}
      >
        <div className="work-flow-controls">
          <p id={`${marker}-help`} role="status">
            {connecting
              ? `Wybierz etap docelowy dla „${byKey.get(connecting)?.label}”. Escape anuluje łączenie.`
              : 'Przeciągaj etapy i łącz je strzałkami. Zadanie może przejść tylko w kierunku strzałki.'}
          </p>
          <div className="work-flow-controls-actions">
            <button
              type="button"
              className="tasks-filter-button"
              disabled={pending || !nodes.length}
              onClick={() => onChange(arrangeWorkflow(data))}
              title="Uporządkuj położenie etapów bez zmiany przejść"
            >
              <Icon name="layout-grid" />
              Uporządkuj
            </button>
            <button
              type="button"
              className="tasks-filter-button"
              disabled={pending || nodes.length < 2}
              onClick={() => {
                onChange(arrangeWorkflow(data, true));
                connect('');
                setNotice(
                  'Przygotowano kolejny przebieg etapów. Zapisz proces lub wybierz Anuluj, aby przywrócić poprzednie przejścia.',
                );
              }}
              title="Zastąp przejścia połączeniami kolejnych etapów. Zmiana wymaga zapisania."
            >
              Połącz kolejno
            </button>
            <button
              type="button"
              className="tasks-filter-button work-flow-icon-button"
              aria-label="Pomniejsz tablicę"
              disabled={zoom <= 0.5}
              onClick={() => setZoom(Math.max(0.5, zoom - 0.1))}
            >
              <Icon name="minus" />
            </button>
            <button
              type="button"
              className="tasks-filter-button"
              onClick={fit}
              title="Dopasuj tablicę do szerokości"
              aria-label="Dopasuj tablicę"
            >
              {Math.round(zoom * 100)}%
            </button>
            <button
              type="button"
              className="tasks-filter-button work-flow-icon-button"
              aria-label="Powiększ tablicę"
              disabled={zoom >= 1.5}
              onClick={() => setZoom(Math.min(1.5, zoom + 0.1))}
            >
              <Icon name="plus" />
            </button>
          </div>
        </div>
        <div
          className="work-flow-viewport"
          ref={viewport}
          role="region"
          aria-label="Tablica procesu pracy"
          aria-describedby={`${marker}-help`}
          tabIndex={0}
        >
          {nodes.length ? (
            <div className="work-flow-sizer" style={{ width: width * zoom, height: height * zoom }}>
              <div
                className="work-flow-canvas"
                ref={canvas}
                style={{ width, height, transform: `scale(${zoom})` }}
              >
                <svg
                  className="work-flow-connections"
                  width={width}
                  height={height}
                  aria-hidden="true"
                >
                  <defs>
                    <marker
                      id={`${marker}-arrow`}
                      viewBox="0 0 10 10"
                      refX="9"
                      refY="5"
                      markerWidth="7"
                      markerHeight="7"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 0 L 10 5 L 0 10 z" />
                    </marker>
                    <marker
                      id={`${marker}-active-arrow`}
                      viewBox="0 0 10 10"
                      refX="9"
                      refY="5"
                      markerWidth="7"
                      markerHeight="7"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 0 L 10 5 L 0 10 z" />
                    </marker>
                  </defs>
                  {edges
                    .sort(
                      (a, b) =>
                        Number(a.source.key === selected) - Number(b.source.key === selected),
                    )
                    .map(({ source, target }, index) => (
                      <path
                        key={`${source.key}:${target.key}`}
                        className={`work-flow-edge${source.key === selected ? ' is-selected' : ''}`}
                        d={transitionPath(source, target, index)}
                        markerEnd={`url(#${marker}-${source.key === selected ? 'active-arrow' : 'arrow'})`}
                      />
                    ))}
                </svg>
                {nodes.map((node) => (
                  <button
                    type="button"
                    key={node.key}
                    className={`work-flow-node${selected === node.key ? ' is-selected' : ''}${connecting && connecting !== node.key ? ' is-target' : ''}`}
                    style={{ left: node.x, top: node.y, width: NODE_WIDTH, height: NODE_HEIGHT }}
                    aria-label={`Etap: ${node.label}`}
                    aria-pressed={selected === node.key}
                    disabled={pending}
                    onClick={() => choose(node.key)}
                    onDoubleClick={() => {
                      if (!pending && !connecting) onEdit(node.index);
                    }}
                    onPointerDown={(event) => start(event, node.key)}
                    onPointerMove={move}
                    onPointerUp={() => end()}
                    onPointerCancel={() => end(true)}
                    onKeyDown={(event) => {
                      if (
                        pending ||
                        connecting ||
                        !event.altKey ||
                        !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)
                      )
                        return;
                      event.preventDefault();
                      const step = event.shiftKey ? 40 : 10;
                      onChange(
                        moveWorkflowNode(data, node.key, {
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
                        }),
                      );
                    }}
                    title={`${node.label}. Przeciągnij lub użyj Alt + strzałek, aby przesunąć. Kliknij dwukrotnie, aby edytować.`}
                  >
                    <span className="work-flow-node-label">
                      <span className={`status-indicator status-${node.category}`} />
                      <span>{node.label}</span>
                    </span>
                    <span className="work-flow-node-meta">
                      {node.stageLabel}
                      {node.limit ? ` · WIP ${node.limit}` : ''}
                    </span>
                    {node.key === initialKey ? (
                      <span className="work-flow-node-start">Początek</span>
                    ) : null}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="work-flow-empty">
              <Icon name="workflow" />
              <p>Brak etapów procesu.</p>
              <p>Dodaj pierwszy etap, aby zbudować przebieg pracy.</p>
            </div>
          )}
        </div>
        <div className="work-flow-inspector" aria-label="Przejścia wybranego etapu">
          {current ? (
            <>
              <div className="work-flow-inspector-heading">
                <span className={`status-indicator status-${current.category}`} />
                <strong>{current.label}</strong>
                <span>{current.stageLabel}</span>
                <span className="work-flow-order">Kolejność: {nodes.indexOf(current) + 1}</span>
                {([-1, 1] as const).map((direction) => (
                  <button
                    type="button"
                    key={direction}
                    className="tasks-filter-button work-flow-icon-button"
                    disabled={
                      pending ||
                      nodes.indexOf(current) === (direction === -1 ? 0 : nodes.length - 1)
                    }
                    aria-label={
                      direction === -1
                        ? 'Przesuń etap wcześniej w kolejności'
                        : 'Przesuń etap później w kolejności'
                    }
                    onClick={() => onMove(current.index, direction)}
                  >
                    <Icon name={direction === -1 ? 'arrow-left' : 'arrow-right'} />
                  </button>
                ))}
              </div>
              <div className="work-flow-outgoing">
                <span>Dozwolone następne etapy:</span>
                {current.transitions
                  .filter((key) => byKey.has(key) && key !== current.key)
                  .map((key) => (
                    <span key={key} className="work-flow-transition">
                      <Icon name="arrow-right" />
                      <button
                        type="button"
                        className="work-configuration-name"
                        onClick={() => select(key)}
                      >
                        {byKey.get(key)!.label}
                      </button>
                      <button
                        type="button"
                        className="tasks-filter-button work-flow-icon-button"
                        disabled={pending}
                        aria-label={`Usuń przejście: ${current.label} → ${byKey.get(key)!.label}`}
                        onClick={() => onChange(connectWorkflow(data, current.key, key, true))}
                      >
                        <Icon name="x" />
                      </button>
                    </span>
                  ))}
                {!current.transitions.some((key) => byKey.has(key) && key !== current.key) ? (
                  <span>Brak — z tego etapu nie można przejść dalej.</span>
                ) : null}
              </div>
              {current.policy ? <p className="work-flow-policy">{current.policy}</p> : null}
            </>
          ) : (
            <p>Wybierz etap, aby zobaczyć jego przejścia, edytować go lub dodać połączenie.</p>
          )}
          <p className="work-flow-notice" role="status">
            {notice ||
              (actions.dirty
                ? 'Niezapisane zmiany procesu.'
                : 'Połączenia określają dostępne akcje w zadaniach.')}
          </p>
        </div>
      </div>
    </>
  );
}
