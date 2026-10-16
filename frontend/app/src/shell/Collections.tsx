import { useId } from 'react';
import { Avatar } from '../shared/Avatar';
import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import type { Collection, CollectionRow, ShellData } from './navigation-types';
interface Actions {
  openForm: (url: string) => void;
  star: (row: CollectionRow) => void;
  busy: boolean;
  picker: (group: Collection, anchor: HTMLElement) => void;
}
export function CollectionContents({
  group,
  data,
  actions,
  flyout = false,
}: {
  group: Collection;
  data: ShellData;
  actions: Actions;
  flyout?: boolean;
}) {
  const prefix = useId();
  const linkClass = flyout ? 'sidebar-collapsed-flyout__link' : 'nav-link sidebar-subnav-link';
  return (
    <>
      {group.key === 'filters' ? (
        <a
          href={group.create_url}
          className={`${linkClass}${data.filter_search_active ? ' active' : ''}`}
          aria-current={data.filter_search_active ? 'page' : undefined}
        >
          <Icon name="search" className="sidebar-subnav-icon" />
          <span>Wyszukaj zadania</span>
        </a>
      ) : null}
      {(
        [
          ['starred', 'Oznaczone gwiazdką', group.starred],
          ['recent', 'Ostatnie', group.recent],
        ] as const
      ).map(([key, title, rows]) =>
        rows.length || (key === 'recent' && group.key === 'pulpits') ? (
          <section key={key} className="sidebar-space-list" aria-labelledby={`${prefix}-${key}`}>
            <h3 id={`${prefix}-${key}`} className="sidebar-space-list-title">
              {title}
            </h3>
            {rows.map((row) => (
              <Row key={row.id} row={row} group={group} actions={actions} linkClass={linkClass} />
            ))}
            {key === 'recent' && group.key === 'pulpits' ? (
              <a
                href={data.default_pulpit_url}
                className={`${linkClass}${data.default_pulpit_active ? ' active' : ''}`}
                aria-current={data.default_pulpit_active ? 'page' : undefined}
                title="Pulpit domyślny"
                data-sidebar-source-item={flyout ? undefined : 'dashboard'}
                draggable={!flyout}
              >
                <Icon name="layout-dashboard" className="sidebar-subnav-icon" />
                <span>Pulpit domyślny</span>
              </a>
            ) : null}
          </section>
        ) : null,
      )}
      <button
        type="button"
        className={`${linkClass} sidebar-spaces-more`}
        aria-haspopup="dialog"
        aria-controls={`sidebar-${group.key}-picker`}
        onClick={(event) => actions.picker(group, event.currentTarget)}
      >
        <Icon name="align-left" className="sidebar-subnav-icon" />
        <span>
          {group.key === 'spaces'
            ? 'Więcej przestrzeni'
            : group.key === 'pulpits'
              ? 'Więcej pulpitów'
              : 'Więcej filtrów'}
        </span>
        <Icon name="chevron-right" className="sidebar-spaces-more__chevron" />
      </button>
      {flyout ? (
        <>
          <a
            href={group.create_url}
            className="sidebar-collapsed-flyout__link"
            onClick={(event) => {
              if (
                group.key !== 'filters' &&
                !event.metaKey &&
                !event.ctrlKey &&
                !event.shiftKey &&
                !event.altKey
              ) {
                event.preventDefault();
                actions.openForm(group.create_url);
              }
            }}
          >
            <Icon name="plus" />
            <span>
              {group.key === 'spaces'
                ? 'Utwórz przestrzeń'
                : group.key === 'pulpits'
                  ? 'Utwórz pulpit'
                  : 'Nowe wyszukiwanie'}
            </span>
          </a>
          {group.manage_url ? (
            <a className="sidebar-collapsed-flyout__link" href={group.manage_url}>
              <Icon name="settings" />
              <span>Zarządzaj: {group.label.toLocaleLowerCase('pl')}</span>
            </a>
          ) : null}
        </>
      ) : null}
    </>
  );
}
function Row({
  row,
  group,
  actions,
  linkClass,
}: {
  row: CollectionRow;
  group: Collection;
  actions: Actions;
  linkClass: string;
}) {
  return (
    <div className="sidebar-space-row" data-sidebar-collection-row={row.id}>
      <a
        href={row.url}
        className={`${linkClass}${row.active ? ' active' : ''}`}
        aria-current={row.active ? 'page' : undefined}
        title={row.name}
      >
        {row.avatar ? (
          <Avatar data={row.avatar} space className="sidebar-subnav-icon" />
        ) : (
          <Icon name={group.icon} className="sidebar-subnav-icon" />
        )}
        <span>{row.name}</span>
      </a>
      <Dropdown
        className="react-sidebar-row-menu"
        label={`Opcje: ${row.name}`}
        triggerClassName="sidebar-header-action sidebar-space-row__toggle"
        trigger={<Icon name="ellipsis" />}
        menuClass="tasks-section-menu sidebar-group-menu sidebar-space-menu"
        searchable={false}
        role="group"
        disabled={actions.busy}
      >
        {(close) => (
          <>
            <button
              type="button"
              className="tasks-project-menu-button"
              onClick={() => {
                close();
                actions.star(row);
              }}
            >
              <Icon name="star" />
              <span>
                {row.favorite ? 'Usuń z oznaczonych gwiazdką' : 'Dodaj do oznaczonych gwiazdką'}
              </span>
            </button>
            {row.members_url ? (
              <a
                href={row.members_url}
                className="tasks-project-menu-button"
                onClick={(event) => {
                  if (!event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
                    event.preventDefault();
                    close();
                    actions.openForm(row.members_url!);
                  }
                }}
              >
                <Icon name="user-round-plus" />
                <span>Dodaj osoby</span>
              </a>
            ) : null}
            {row.settings_url ? (
              <a href={row.settings_url} className="tasks-project-menu-button" onClick={close}>
                <Icon name="settings" />
                <span>Ustawienia przestrzeni</span>
              </a>
            ) : null}
            {row.actions?.map((item) => (
              <a
                key={item.url}
                href={item.url}
                className="tasks-project-menu-button"
                onClick={close}
              >
                <Icon name={item.icon} />
                <span>{item.label}</span>
              </a>
            ))}
            {row.description ? (
              <div className="sidebar-space-menu__summary">
                {row.avatar ? <Avatar data={row.avatar} space /> : null}
                <div>
                  <strong>{row.description}</strong>
                  <span>{row.detail}</span>
                </div>
              </div>
            ) : null}
          </>
        )}
      </Dropdown>
    </div>
  );
}
export function CollectionGroup({
  group,
  data,
  actions,
  collapsed,
  flyout,
  flyoutOpen = false,
  onToggle,
}: {
  group: Collection;
  data: ShellData;
  actions: Actions;
  collapsed: boolean;
  flyout: boolean;
  flyoutOpen?: boolean;
  onToggle: (button: HTMLElement, keyboard: boolean) => void;
}) {
  const label = `${flyout ? (flyoutOpen ? 'Zamknij menu' : 'Otwórz menu') : collapsed ? 'Rozwiń sekcję' : 'Zwiń sekcję'} ${group.label}`;
  return (
    <section
      className={`sidebar-nav-group sidebar-nav-group--collection${collapsed ? ' is-collapsed' : ''}${flyoutOpen ? ' is-flyout-open' : ''}`}
      data-sidebar-group={group.key}
      aria-labelledby={`sidebar-${group.key}-title`}
    >
      <div className="sidebar-group-header">
        <button
          type="button"
          className="nav-link sidebar-primary-link sidebar-group-toggle"
          aria-label={label}
          title={label}
          aria-controls={flyout ? 'sidebar-collapsed-flyout' : `sidebar-${group.key}-subnav`}
          aria-expanded={flyout ? flyoutOpen : !collapsed}
          data-sidebar-group-toggle
          onClick={(event) => onToggle(event.currentTarget, event.detail === 0)}
        >
          <Icon name={group.icon} className="nav-icon sidebar-spaces-icon" />
          <Icon name="chevron-down" className="nav-icon sidebar-spaces-chevron" />
          <span id={`sidebar-${group.key}-title`} className="nav-label">
            {group.label}
          </span>
        </button>
        <div className="sidebar-header-actions sidebar-group-actions">
          <a
            className="sidebar-header-action"
            href={group.create_url}
            aria-label={
              group.key === 'spaces'
                ? 'Utwórz przestrzeń'
                : group.key === 'pulpits'
                  ? 'Utwórz pulpit'
                  : 'Nowe wyszukiwanie'
            }
            title={
              group.key === 'spaces'
                ? 'Utwórz przestrzeń'
                : group.key === 'pulpits'
                  ? 'Utwórz pulpit'
                  : 'Nowe wyszukiwanie'
            }
            onClick={(event) => {
              if (
                group.key !== 'filters' &&
                !event.ctrlKey &&
                !event.metaKey &&
                !event.shiftKey &&
                !event.altKey
              ) {
                event.preventDefault();
                actions.openForm(group.create_url);
              }
            }}
          >
            <Icon name="plus" />
          </a>
          <Dropdown
            className="react-sidebar-row-menu"
            triggerClassName="sidebar-header-action"
            trigger={<Icon name="ellipsis" />}
            label={`Opcje: ${group.label}`}
            role="group"
            menuClass="tasks-section-menu sidebar-group-menu"
            searchable={false}
          >
            {(close) =>
              group.manage_url ? (
                <a href={group.manage_url} className="tasks-project-menu-button" onClick={close}>
                  <Icon name="settings" />
                  <span>
                    {group.key === 'spaces'
                      ? 'Zarządzaj przestrzeniami'
                      : group.key === 'pulpits'
                        ? 'Zarządzaj pulpitami'
                        : 'Zarządzaj filtrami'}
                  </span>
                </a>
              ) : (
                <p className="sidebar-workspace-search__empty">Brak dostępnych działań.</p>
              )
            }
          </Dropdown>
        </div>
      </div>
      <div
        id={`sidebar-${group.key}-subnav`}
        className={`sidebar-subnav sidebar-subnav--extended sidebar-subnav--spaces${group.key === 'pulpits' ? ' sidebar-subnav--pulpits' : ''}`}
        aria-label={group.label}
        hidden={collapsed || flyout}
      >
        <CollectionContents group={group} data={data} actions={actions} />
      </div>
    </section>
  );
}
