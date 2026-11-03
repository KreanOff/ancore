import { issueTypeBadgeStyle } from '../shared/issue-type-color';
import { EmptyState } from '../shared/EmptyState';
import { useLayoutEffect, useRef, useState } from 'react';
import { Avatar, type AvatarData } from '../shared/Avatar';
import { Icon } from '../shared/Icon';
import type { PageProps } from '../shared/page';
import { StatusGroup } from '../shared/StatusGroup';
import { dateLabel } from '../spaces/types';
interface Space {
  id: number;
  name: string;
  key: string;
  kind: string;
  avatar: AvatarData;
  url: string;
  count: number;
  description: string;
}
interface Row {
  title: string;
  url: string;
  location: string;
  icon: string;
  is_task: boolean;
  key: string;
  status_label: string;
  overdue: boolean;
  due_at?: string;
  recent_at?: string;
  space?: Space;
  task?: {
    status: string;
    priority: string;
    priority_label?: string;
    type_label: string;
    type_icon: string;
    type_color?: string;
    tags_count: number;
    attachments_count: number;
    due_urgency: string;
  };
}
interface Data {
  projects: Row[];
  projects_url: string;
  tab: string;
  tabs: { key: string; label: string; icon: string; url: string }[];
  groups: {
    date_group: string;
    task_groups: { category: string; label: string; items: Row[] }[];
    spaces: Space[];
    other_rows: Row[];
  }[];
  assigned_count: number;
  empty: [string, string];
  illustration: string;
  spaces_illustration: string;
  filtered: boolean;
  clear_url: string;
  previous: string;
  next: string;
}
export function ForYouTaskRow({ row, selectable = false }: { row: Row; selectable?: boolean }) {
  const task = row.task!;
  const [selected, setSelected] = useState(false);
  const priority: Record<string, string> = {
    urgent: 'circle-alert',
    high: 'arrow-up',
    medium: 'equal',
    low: 'arrow-down',
  };
  return (
    <article
      className={`tasks-issue-row work-issue-row ${selectable ? '' : 'work-issue-row--unselectable'} ${task.status === 'closed' ? 'completed' : ''} ${selected ? 'checked' : ''}`}
    >
      {selectable ? (
        <input
          type="checkbox"
          className="tasks-row-checkbox"
          aria-label={`Zaznacz ${row.key} · ${row.title}`}
          checked={selected}
          onChange={(event) => setSelected(event.target.checked)}
        />
      ) : null}
      <span
        className={`tasks-row-priority priority-${task.priority}`}
        title={`Priorytet: ${task.priority_label || task.priority}`}
      >
        <span className="tasks-priority-icon">
          <Icon name={priority[task.priority] || 'circle'} />
        </span>
      </span>
      <a href={row.url} className="work-item-key" title={`${row.key} · ${row.title}`}>
        {row.key}
      </a>
      <span
        className={`status-indicator status-${task.status}`}
        title={row.status_label}
        aria-label={row.status_label}
      />
      <a
        href={row.url}
        className="tasks-row-title"
        title={`${row.key} · ${row.title} · ${row.location}`}
      >
        <span className="tasks-row-title-content">
          <span className="tasks-row-title-main">
            <span className="tasks-row-title-text">{row.title}</span>
          </span>
        </span>
      </a>
      <span
        className="tasks-issue-type"
        style={issueTypeBadgeStyle(task.type_color)}
        title={`Typ zgłoszenia: ${task.type_label}`}
      >
        <Icon name={task.type_icon} />
        <span>{task.type_label}</span>
      </span>
      <span className="tasks-row-tags" title={`Tagi: ${task.tags_count}`}>
        <Icon name="tag" />
        {task.tags_count}
      </span>
      <span className="tasks-row-attachments" title={`Załączniki: ${task.attachments_count}`}>
        <Icon name="paperclip" />
        {task.attachments_count}
      </span>
      <span
        className={`tasks-row-date tasks-row-due tasks-row-due--${task.due_urgency}`}
        title={row.due_at ? `Termin: ${dateLabel(row.due_at, true)}` : 'Brak terminu'}
      >
        {row.due_at ? <Icon name="flame" /> : null}
      </span>
    </article>
  );
}
function SpaceRows({ spaces }: { spaces: Space[] }) {
  return (
    <div
      className="tasks-table-wrap tasks-board tasks-directory-board tasks-directory-sheet tasks-project-sheet tasks-project-sheet--selectable tasks-directory-menu-sheet tasks-spreadsheet-sheet work-space-sheet work-space-sheet--compact work-space-sheet--unselectable work-space-sheet--no-actions for-you-space-sheet"
      data-directory-resize="false"
    >
      <section className="tasks-directory-group" role="table" aria-label="Lista przestrzeni">
        <div className="tasks-directory-header" role="row">
          {[
            ['name', 'PRZESTRZEŃ', 'layers'],
            ['key', 'KLUCZ', 'hash'],
            ['description', 'OPIS', 'align-left'],
          ].map(([key, label, icon]) => (
            <span
              key={key}
              className="tasks-directory-sheet__cell tasks-project-sheet__cell"
              data-column={key}
              role="columnheader"
            >
              {label}
              <Icon name={icon} />
            </span>
          ))}
        </div>
        <div className="tasks-issue-list tasks-directory-list" role="rowgroup">
          {spaces.map((space) => (
            <article
              className="tasks-issue-row tasks-directory-row work-space-row"
              role="row"
              key={space.id}
            >
              <span
                className="tasks-directory-sheet__cell tasks-directory-name"
                data-column="name"
                role="cell"
              >
                <Avatar space data={space.avatar} />
                <a href={space.url} title={space.name}>
                  {space.name}
                </a>
              </span>
              <span className="tasks-directory-sheet__cell" data-column="key" role="cell">
                {space.key}
              </span>
              <span
                className="tasks-directory-sheet__cell tasks-project-sheet__description"
                data-column="description"
                role="cell"
                title={space.description}
              >
                {space.description || 'Brak opisu'}
              </span>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
export default function ForYouPage({ initial }: PageProps) {
  const data = initial.data as Data;
  const tabs = useRef<HTMLElement>(null);
  useLayoutEffect(() => {
    const nav = tabs.current!,
      active = nav.querySelector<HTMLElement>('[aria-current="page"]');
    const reveal = () => {
      if (!active) return;
      const left = active.offsetLeft,
        right = left + active.offsetWidth;
      if (left < nav.scrollLeft) nav.scrollLeft = left;
      else if (right > nav.scrollLeft + nav.clientWidth) nav.scrollLeft = right - nav.clientWidth;
    };
    reveal();
    const observer = new ResizeObserver(reveal);
    observer.observe(nav);
    return () => observer.disconnect();
  }, [data.tab]);
  return (
    <div
      className={`dashboard-page dashboard-overview for-you-page ${!data.projects.length && !data.groups.length ? 'for-you-page--empty' : ''}`}
      data-react-screen="for-you"
    >
      <header className="tasks-topbar tasks-topbar--project-directory">
        <div className="tasks-titlebar-left">
          <h1 className="tasks-topbar-title">Dla ciebie</h1>
        </div>
      </header>
      <div className="dashboard-main">
        <section aria-labelledby="for-you-projects-title">
          <div className="for-you-section-heading">
            <h2 id="for-you-projects-title">Rekomendowane przestrzenie</h2>
            <a className="dashboard-panel-link" href={data.projects_url}>
              Wszystkie przestrzenie
              <Icon name="arrow-up-right" />
            </a>
          </div>
          {data.projects.length ? (
            <div className="for-you-project-grid">
              {data.projects.map((row) => (
                <article className="dashboard-panel for-you-project" key={row.url}>
                  <a className="for-you-project-heading" href={row.url}>
                    {row.space ? (
                      <Avatar space data={row.space.avatar} className="space-avatar--heading" />
                    ) : (
                      <Icon name={row.icon} />
                    )}
                    <span className="dashboard-task-main">
                      <strong title={row.title}>{row.title}</strong>
                      <small>{row.space?.kind || row.status_label}</small>
                    </span>
                  </a>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState
              className="for-you-spaces-empty"
              src={data.spaces_illustration}
              title="Brak rekomendowanych przestrzeni"
              description="Otwórz przestrzeń lub dodaj ją do ulubionych, aby mieć ją pod ręką."
            />
          )}
        </section>
        <section className="dashboard-panel for-you-work-panel" aria-label="Twoja praca">
          <nav
            ref={tabs}
            className="notifications-tabs work-tabs for-you-tabs"
            aria-label="Widok dla ciebie"
          >
            {data.tabs.map((tab) => (
              <a
                key={tab.key}
                href={tab.url}
                aria-current={data.tab === tab.key ? 'page' : undefined}
              >
                <Icon name={tab.icon} />
                {tab.label}
                {tab.key === 'assigned' ? (
                  <span className="for-you-count">{data.assigned_count}</span>
                ) : null}
              </a>
            ))}
          </nav>
          <div className="for-you-task-list">
            {data.groups.length ? (
              data.groups.map((block, index) => (
                <div key={block.date_group || index}>
                  {block.date_group ? (
                    <h3 className="tasks-space-group-title for-you-date-heading">
                      <span>{block.date_group}</span>
                    </h3>
                  ) : null}
                  {block.task_groups.length ? (
                    <div className="tasks-table-wrap tasks-board for-you-status-groups">
                      {block.task_groups.map((group, index) => (
                        <StatusGroup
                          key={index}
                          category={group.category}
                          label={group.label}
                          count={group.items.length}
                        >
                          <div className="tasks-issue-list">
                            {group.items.map((row) => (
                              <ForYouTaskRow key={row.url} row={row} />
                            ))}
                          </div>
                        </StatusGroup>
                      ))}
                    </div>
                  ) : null}
                  {block.spaces.length ? (
                    <div className="tasks-table-wrap tasks-board for-you-space-groups">
                      <StatusGroup
                        className="for-you-space-group"
                        label="Przestrzenie"
                        count={block.spaces.length}
                      >
                        <div className="tasks-issue-list">
                          <SpaceRows spaces={block.spaces} />
                        </div>
                      </StatusGroup>
                    </div>
                  ) : null}
                  {block.other_rows.map((row) => (
                    <a key={row.url} className="dashboard-task-item for-you-item" href={row.url}>
                      <Icon name={row.icon} />
                      <span className="dashboard-task-main">
                        <strong>{row.title}</strong>
                        <small>
                          {row.key} · {row.location}
                        </small>
                      </span>
                      <span className="dashboard-task-state">
                        {row.recent_at || row.due_at ? (
                          <time>{dateLabel((row.recent_at || row.due_at)!, true)}</time>
                        ) : null}
                      </span>
                      <Icon name="chevron-right" />
                    </a>
                  ))}
                </div>
              ))
            ) : (
              <EmptyState
                src={data.illustration}
                title={data.filtered ? 'Brak pasujących wyników' : data.empty[0]}
                description={
                  data.filtered
                    ? 'Wyczyść filtry, aby wrócić do pełnej listy tej zakładki.'
                    : data.empty[1]
                }
              />
            )}
          </div>
          {data.previous || data.next ? (
            <nav
              className="dashboard-overview-list-footer for-you-pagination"
              aria-label="Paginacja twojej pracy"
            >
              <div>
                {data.previous ? (
                  <a
                    className="tasks-filter-button"
                    href={data.previous}
                    aria-label="Poprzednia strona"
                  >
                    <Icon name="chevron-left" />
                  </a>
                ) : null}
                {data.next ? (
                  <a className="tasks-filter-button" href={data.next} aria-label="Następna strona">
                    <Icon name="chevron-right" />
                  </a>
                ) : null}
              </div>
            </nav>
          ) : null}
        </section>
      </div>
    </div>
  );
}
