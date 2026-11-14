import { issueTypeBadgeStyle } from '../shared/issue-type-color';
import { statusColorStyle } from '../shared/status-color';
import { type DragEvent } from 'react';
import { Avatar } from '../shared/Avatar';
import { Icon } from '../shared/Icon';
import { dateLabel, type DetailData, type Item } from './types';
import { flowAge } from './kanban';
import { TaskPriority as Priority } from '../shared/TaskPriority';
export { Priority };
export function ItemType({ item }: { item: Item }) {
  return (
    <span
      className="tasks-issue-type"
      style={issueTypeBadgeStyle(item.type_color)}
      title={`Typ zgłoszenia: ${item.type_label}`}
    >
      <Icon name={item.type_icon} />
      <span>{item.type_label}</span>
    </span>
  );
}
function Planning({
  item,
  scrum,
  showAssigneeName = false,
}: {
  item: Item;
  scrum: boolean;
  showAssigneeName?: boolean;
}) {
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
      <span
        className={`work-backlog-assignee${showAssigneeName ? ' work-backlog-assignee--named' : ''}`}
        title={item.assignee?.label || 'Brak wykonawcy'}
      >
        {item.assignee ? (
          <Avatar data={item.assignee.avatar} className="tasks-issue-mini-avatar" />
        ) : (
          <Icon name="user" />
        )}
        {showAssigneeName ? (
          <span className="work-assignee-name">{item.assignee?.label || 'Nie przypisano'}</span>
        ) : null}
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
}

function ItemIdentity({ item }: { item: Item }) {
  return (
    <>
      <Priority value={item.priority} label={item.priority_label} />
      <a href={item.url} className="work-item-key" title={`${item.key} · ${item.title}`}>
        {item.key}
      </a>
      <span
        className={`status-indicator status-${item.category}`}
        style={statusColorStyle(item.status_color)}
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
            <span className="tasks-row-title-text">{item.title}</span>
            {item.blocked ? (
              <span
                className="work-blocked-indicator"
                title={`Zablokowane: ${item.blocked.reason}`}
                aria-label={`Zablokowane: ${item.blocked.reason}`}
              >
                <Icon name="circle-alert" />
              </span>
            ) : null}
          </span>
        </span>
      </a>
    </>
  );
}
export function TimelineItemRow({ item }: { item: Item }) {
  return (
    <article
      className={`tasks-issue-row work-issue-row work-issue-row--timeline ${item.category === 'closed' ? 'completed' : ''}`}
    >
      <ItemIdentity item={item} />
      <Planning item={item} scrum={false} showAssigneeName />
    </article>
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
      className={`tasks-issue-row work-issue-row work-issue-row--planning ${planning && item.editable && data.sort.manual ? 'work-issue-row--draggable' : ''} ${item.category === 'closed' ? 'completed' : ''} ${selected ? 'checked' : ''}`}
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
      <ItemIdentity item={item} />
      <ItemType item={item} />
      <Planning item={item} scrum={data.space.template === 'scrum'} />
      <Counts item={item} />
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
      <a href={item.url} className="work-item-key" title={`${item.key} · ${item.title}`}>
        {item.key}
      </a>
      <span
        className={`status-indicator status-${item.category}`}
        style={statusColorStyle(item.status_color)}
        title={item.status_label}
      />
      <a href={item.url} className="tasks-row-title">
        {item.title}
      </a>
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
      {item.blocked ? (
        <div className="work-card-blocked" aria-label="Blokada zadania">
          <span>
            <Icon name="circle-alert" /> Zablokowane · {flowAge(item.blocked.at)}
          </span>
          <span className="work-card-blocked-reason" title={item.blocked.reason}>
            {item.blocked.reason}
          </span>
          {item.blocked.responsible ? (
            <span>Odpowiedzialny: {item.blocked.responsible.label}</span>
          ) : null}
        </div>
      ) : null}
      {item.flow?.stage_entered_at && item.category !== 'closed' ? (
        <div
          className="work-card-age"
          title={`W etapie od ${dateLabel(item.flow.stage_entered_at, true)}`}
        >
          <Icon name="clock" /> W etapie: {flowAge(item.flow.stage_entered_at)}
        </div>
      ) : null}
    </article>
  );
}
