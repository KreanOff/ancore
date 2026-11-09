import type { ComponentProps, FormHTMLAttributes, HTMLAttributes, ReactNode } from 'react';
import { Dropdown } from './Dropdown';
import { Icon } from './Icon';

type ToolbarMenuProps = Omit<ComponentProps<typeof Dropdown>, 'trigger'>;

export function ToolbarFilter({
  active = false,
  ...props
}: ToolbarMenuProps & { active?: boolean }) {
  return (
    <Dropdown
      role="dialog"
      layer={false}
      searchable={false}
      menuClass="tasks-project-query-panel"
      {...props}
      triggerClassName={`tasks-filter-button${active ? ' is-active' : ''}`}
      trigger={
        <>
          <Icon name="list-filter" />
          <span>Filtruj</span>
          <Icon name="chevron-down" />
        </>
      }
    />
  );
}

export function ToolbarSort({ current, ...props }: ToolbarMenuProps & { current: string }) {
  return (
    <Dropdown
      {...props}
      trigger={
        <>
          <Icon name="arrow-up-down" />
          <span>Sortuj</span>
          <span className="tasks-project-sort-current">{current}</span>
          <Icon name="chevron-down" />
        </>
      }
    />
  );
}

interface ToolbarSlots {
  filters?: ReactNode;
  actions?: ReactNode;
  search?: ReactNode;
}

function ToolbarContents({ filters, actions, search }: ToolbarSlots) {
  return (
    <>
      {filters ? <div className="tasks-filterbar-left app-toolbar__controls">{filters}</div> : null}
      {search ? <div className="tasks-filterbar-right app-toolbar__search">{search}</div> : null}
      {actions ? <div className="app-toolbar__actions">{actions}</div> : null}
    </>
  );
}

/** Non-form toolbar, including screens with a separate search form. */
export function Toolbar({
  filters,
  actions,
  search,
  children,
  className = '',
  ...props
}: HTMLAttributes<HTMLDivElement> & ToolbarSlots) {
  return (
    <div
      {...props}
      className={`tasks-filterbar tasks-filterbar--directory app-toolbar ${className}`}
    >
      {children}
      <ToolbarContents filters={filters} actions={actions} search={search} />
    </div>
  );
}

export function DirectoryToolbar({
  filters,
  actions,
  search,
  children,
  className = '',
  ...props
}: FormHTMLAttributes<HTMLFormElement> & ToolbarSlots) {
  return (
    <form
      {...props}
      className={`tasks-filterbar tasks-filterbar--directory work-item-toolbar app-toolbar ${className}`}
    >
      {children}
      <ToolbarContents filters={filters} actions={actions} search={search} />
    </form>
  );
}
