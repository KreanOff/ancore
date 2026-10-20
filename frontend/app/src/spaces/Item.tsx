import { type DragEvent } from 'react';
import { Avatar } from '../shared/Avatar';
import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import { dateLabel, type DetailData, type Item } from './types';
export function Priority({ value, label = value }: { value: string; label?: string }) {
  const icons: Record<string, string> = {
    urgent: 'circle-alert',
    high: 'arrow-up',
    medium: 'equal',
    low: 'arrow-down',
  };
  return (
    <span
      className={`tasks-row-priority priority-${value}`}
      title={`Priorytet: ${label}`}
      aria-label={`Priorytet: ${label}`}
    >
      <span className="tasks-priority-icon">
        <Icon name={icons[value] || 'circle'} />
      </span>
    </span>
  );
}
export function ItemType({ item }: { item: Item }) {
  return (
    <span className="tasks-issue-type" title={`Typ zgłoszenia: ${item.type_label}`}>
      <Icon name={item.type_icon} />
      <span>{item.type_label}</span>
    </span>
  );
}
function Planning({ item, scrum }: { item: Item; scrum: boolean }) {
  return (
    <>
      {scrum ? (
        <span
          className="work-item-points"
          title={item.points === null ? 'Brak estymacji' : `Estymacja: ${item.points} pkt`}
        >
          {item.points ?? '—'}
        </span>
      ) : null}
      <span className="work-backlog-assignee" title={item.assignee?.label || 'Brak wykonawcy'}>
        {item.assignee ? (
          <Avatar data={item.assignee.avatar} className="tasks-issue-mini-avatar" />
        ) : (
          <Icon name="user" />
        )}
      </span>
    </>
  );
}
function Counts({ item }: { item: Item }) {
  return (
    <>
      <span className="tasks-row-tags" title={`Tagi: ${item.tags_count}`}>
        <Icon name="tag" />
        {item.tags_count}
      </span>
      <span className="tasks-row-attachments" title={`Załączniki: ${item.attachments_count}`}>
        <Icon name="paperclip" />
        {item.attachments_count}
      </span>
      <span
        className={`tasks-row-date tasks-row-due tasks-row-due--${item.due_urgency}`}
        title={item.due_at ? `Termin: ${dateLabel(item.due_at, true)}` : 'Brak terminu'}
      >
        {item.due_at ? <Icon name="flame" /> : null}
      </span>
    </>
  );
}
export interface ActionsProps {
  item: Item;
  data: DetailData;
  busy: boolean;
  openForm: (url: string) => void;
  act: (url: string, values: Record<string, string>) => void;
}
export function ItemActions({ item, data, busy, openForm, act }: ActionsProps) {
  if (!item.editable) return null;
  const snapshot = {
    space: String(data.space.id),
    source_status: item.status,
    status: item.status,
    source_sprint: String(item.sprint_id ?? ''),
    source_rank: String(item.rank),
    return_view: data.view,
  };
  return (
    <Dropdown
      label={`Działania ${item.key}`}
      className="work-item-actions"
      menuClass="documents-item-menu"
      role="group"
      trigger={<Icon name="menu" />}
    >
      {(close) => (
        <div className="documents-menu-actions">
          <a className="tasks-project-menu-button" href={item.url}>
            <Icon name="external-link" />
            <span>Otwórz zadanie</span>
          </a>
          <button
            type="button"
            className="tasks-project-menu-button"
            disabled={busy}
            onClick={() => {
              close();
              openForm(item.edit_url);
            }}
          >
            <Icon name="pencil" />
            <span>Edytuj {item.key}</span>
          </button>
          {item.transitions.map((status) => (
            <button
              key={status.key}
              type="button"
              className="tasks-project-menu-button"
              disabled={busy}
              onClick={() => {
                close();
                act(item.action_url, {
                  action: 'status',
                  status: status.key,
                  return_view: data.view,
                });
              }}
            >
              <span className={`status-indicator status-${status.category}`} />
              <span>Zmień na: {status.label}</span>
            </button>
          ))}
          {data.sort.manual && ['board', 'backlog'].includes(data.view)
            ? ['up', 'down'].map((direction, index) => (
                <button
                  key={direction}
                  type="button"
                  className="tasks-project-menu-button"
                  disabled={busy}
                  onClick={() => {
                    close();
                    act(item.action_url, {
                      ...snapshot,
                      action: data.view === 'board' ? 'position' : direction,
                      direction,
                    });
                  }}
                >
                  <Icon name={`arrow-${direction}`} />
                  <span>{index ? 'Przesuń niżej' : 'Przesuń wyżej'}</span>
                </button>
              ))
            : null}
          {data.view === 'backlog' && data.space.template === 'scrum'
            ? [{ id: null, name: 'backlogu' }, ...data.sprints.filter((s) => s.state !== 'closed')]
                .filter((s) => s.id !== item.sprint_id)
                .map((sprint) => (
                  <button
                    key={String(sprint.id)}
                    type="button"
                    className="tasks-project-menu-button"
                    disabled={busy}
                    onClick={() => {
                      close();
                      if (!data.sort.manual) {
                        act(data.bulk_plan_url, {
                          item_ids: String(item.id),
                          destination: String(sprint.id ?? ''),
                          positions: JSON.stringify({ [item.id]: [item.sprint_id, item.rank] }),
                        });
                        return;
                      }
                      const target = data.items.filter(
                        (row) => row.sprint_id === sprint.id && row.id !== item.id,
                      );
                      act(item.action_url, {
                        ...snapshot,
                        action: 'plan',
                        sprint: String(sprint.id ?? ''),
                        before: '',
                        after: String(target.at(-1)?.id ?? ''),
                      });
                    }}
                  >
                    <Icon name="arrow-right" />
                    <span>
                      {sprint.id ? `Przenieś do sprintu: ${sprint.name}` : 'Przenieś do backlogu'}
                    </span>
                  </button>
                ))
            : null}
          {data.space.template === 'kanban' ? (
            <button
              type="button"
              className="tasks-project-menu-button"
              disabled={busy}
              onClick={() => {
                close();
                act(item.action_url, {
                  action: item.in_backlog ? 'board' : 'backlog',
                  return_view: data.view,
                });
              }}
            >
              <Icon name="arrow-right" />
              <span>{item.in_backlog ? 'Przenieś na tablicę' : 'Przenieś do backlogu'}</span>
            </button>
          ) : null}
        </div>
      )}
    </Dropdown>
  );
}
interface RowProps extends ActionsProps {
  selected: boolean;
  select: (checked: boolean) => void;
  dragging?: boolean;
  onDragStart?: (event: DragEvent) => void;
  onDragEnd?: () => void;
  onDrop?: (event: DragEvent) => void;
}
export function ItemRow(props: RowProps) {
  const { item, data, selected, select } = props,
    planning = data.view === 'backlog';
  return (
    <article
      data-work-motion-item={item.id}
      className={`tasks-issue-row work-issue-row work-issue-row--planning ${item.editable ? 'work-issue-row--actions' : ''} ${planning && item.editable && data.sort.manual ? 'work-issue-row--draggable' : ''} ${item.category === 'closed' ? 'completed' : ''} ${selected ? 'checked' : ''}`}
      draggable={planning && item.editable && data.sort.manual && !props.busy}
      onDragStart={props.onDragStart}
      onDragEnd={props.onDragEnd}
      onDragOver={
        props.dragging
          ? (event) => {
              event.preventDefault();
              event.stopPropagation();
            }
          : undefined
      }
      onDrop={props.onDrop}
    >
      <input
        type="checkbox"
        className="tasks-row-checkbox"
        aria-label={`Zaznacz ${item.key} · ${item.title}`}
        checked={selected}
        disabled={planning && !item.editable}
        onChange={(event) => select(event.target.checked)}
      />
      <Priority value={item.priority} label={item.priority_label} />
      <span
        className={`status-indicator status-${item.category}`}
        title={item.status_label}
        aria-label={item.status_label}
      />
      <a
        href={item.url}
        className="tasks-row-title"
        title={`${item.key} · ${item.title} · ${item.type_label}`}
      >
        <span className="tasks-row-title-content">
          <span className="tasks-row-title-main">
            <span className="work-item-key">{item.key}</span>
            <span className="tasks-row-title-text">{item.title}</span>
          </span>
        </span>
      </a>
      <ItemType item={item} />
      <Planning item={item} scrum={data.space.template === 'scrum'} />
      <Counts item={item} />
      <ItemActions {...props} />
    </article>
  );
}
export function ItemCard(
  props: ActionsProps & {
    dragging: boolean;
    onDragStart: (event: DragEvent) => void;
    onDragEnd: () => void;
    onDrop: (event: DragEvent) => void;
  },
) {
  const { item, data } = props,
    scrum = data.space.template === 'scrum';
  const drag = {
    'data-work-motion-item': item.id,
    draggable: item.editable && data.sort.manual && !props.busy,
    onDragStart: props.onDragStart,
    onDragEnd: props.onDragEnd,
    onDragOver: props.dragging
      ? (event: DragEvent) => {
          event.preventDefault();
          event.stopPropagation();
        }
      : undefined,
    onDrop: props.onDrop,
  };
  return (
    <article
      className={`tasks-issue-row work-issue-row work-sprint-card ${item.category === 'closed' ? 'completed' : ''}`}
      {...drag}
    >
      <Priority value={item.priority} label={item.priority_label} />
      <span className={`status-indicator status-${item.category}`} title={item.status_label} />
      <a href={item.url} className="tasks-row-title">
        <span className="work-item-key">{item.key}</span> {item.title}
      </a>
      <ItemActions {...props} />
      <div className="work-sprint-card-meta" aria-label="Metadane zadania">
        <ItemType item={item} />
        <Planning item={item} scrum={scrum} />
        <Counts item={item} />
      </div>
      {item.team ? (
        <div className="work-kanban-context work-sprint-card-context">
          <span>{item.team}</span>
        </div>
      ) : null}
    </article>
  );
}
