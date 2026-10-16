import type { DragEvent } from 'react';
import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import type { Gadget as GadgetData, Layout } from './types';
export function LayoutPreview({ value }: { value: Layout }) {
  return (
    <span className={`pulpit-layout-preview pulpit-layout-preview--${value}`} aria-hidden="true">
      <span />
      <span />
      <span />
    </span>
  );
}
export default function Gadget({
  data,
  editing,
  busy,
  first,
  last,
  single,
  dragging,
  open,
  move,
  remove,
  dragStart,
  dragEnd,
}: {
  data: GadgetData;
  editing: boolean;
  busy: boolean;
  first: boolean;
  last: boolean;
  single: boolean;
  dragging: boolean;
  open: () => void;
  move: (direction: string) => void;
  remove: () => void;
  dragStart: (event: DragEvent) => void;
  dragEnd: () => void;
}) {
  return (
    <article
      className={`dashboard-panel pulpit-gadget ${dragging ? 'is-dragging' : ''}`}
      data-gadget-id={data.id}
    >
      <header className="dashboard-panel-header pulpit-gadget-header">
        {editing ? (
          <button
            type="button"
            className="tasks-icon-button pulpit-drag-handle"
            draggable={!busy}
            disabled={busy}
            aria-label={`Przeciągnij gadżet: ${data.label}`}
            title="Przeciągnij gadżet"
            onDragStart={dragStart}
            onDragEnd={dragEnd}
          >
            <Icon name="grip-vertical" />
          </button>
        ) : null}
        <h2>{data.label}</h2>
        <Icon name={data.icon} />
        {editing ? (
          <Dropdown
            label={`Działania gadżetu: ${data.label}`}
            className="documents-item-actions"
            triggerClassName="tasks-icon-button documents-icon-button"
            menuClass="tasks-section-menu documents-item-menu"
            role="group"
            trigger={<Icon name="ellipsis" />}
          >
            {(close) => (
              <div className="documents-menu-actions">
                <button
                  type="button"
                  className="tasks-project-menu-button"
                  disabled={busy}
                  onClick={() => {
                    close();
                    open();
                  }}
                >
                  <Icon name="settings-2" />
                  <span>Konfiguruj</span>
                </button>
                {[
                  ['up', 'Przenieś wyżej', 'arrow-up'],
                  ['down', 'Przenieś niżej', 'arrow-down'],
                  ['column', 'Do następnej kolumny', 'arrow-right'],
                ].map(([direction, label, icon]) => (
                  <button
                    key={direction}
                    type="button"
                    className="tasks-project-menu-button"
                    disabled={
                      busy ||
                      (direction === 'up' && first) ||
                      (direction === 'down' && last) ||
                      (direction === 'column' && single)
                    }
                    onClick={() => {
                      close();
                      move(direction);
                    }}
                  >
                    <Icon name={icon} />
                    <span>{label}</span>
                  </button>
                ))}
                <button
                  type="button"
                  className="tasks-project-menu-button"
                  disabled={busy}
                  onClick={() => {
                    close();
                    remove();
                  }}
                >
                  <Icon name="trash-2" />
                  <span>Usuń gadżet</span>
                </button>
              </div>
            )}
          </Dropdown>
        ) : null}
      </header>
      {data.unavailable ? (
        <div className="pulpit-gadget-body">
          <div className="pulpit-gadget-empty-state">
            <Icon name="lock" className="pulpit-gadget-empty-icon" />
            <p className="pulpit-gadget-empty">
              Nie masz dostępu do źródłowej przestrzeni tego gadżetu.
            </p>
          </div>
        </div>
      ) : (
        <div className="dashboard-overview-progress">
          <div className="dashboard-overview-progress-total">
            <strong>
              {data.percent}
              <span>%</span>
            </strong>
            <span>
              Zamknięte: {data.closed_count} z {data.count}
            </span>
          </div>
          <progress max={100} value={data.percent} aria-label="Odsetek zamkniętych zadań">
            {data.percent}%
          </progress>
          <p className="dashboard-overview-caption">{data.caption}</p>
          <dl className="dashboard-overview-statuses">
            {data.statuses?.map((status) => (
              <div key={status.key}>
                <dt>
                  <span className={`status-indicator status-${status.key}`} aria-hidden="true" />
                  {status.label}
                </dt>
                <dd>{status.count}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </article>
  );
}
