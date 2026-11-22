import {
  forwardRef,
  type ComponentProps,
  type FormHTMLAttributes,
  type HTMLAttributes,
  type ReactNode,
} from 'react';
import { Dropdown } from './Dropdown';
import { Icon } from './Icon';

type ToolbarMenuProps = Omit<ComponentProps<typeof Dropdown>, 'trigger'>;

export function ToolbarFilter({
  active = false,
  activeCount = 0,
  ...props
}: ToolbarMenuProps & { active?: boolean; activeCount?: number }) {
  return (
    <Dropdown
      role="dialog"
      layer={false}
      searchable={false}
      menuClass="tasks-project-query-panel"
      {...props}
      triggerClassName={`tasks-filter-button${active || activeCount > 0 ? ' is-active' : ''}`}
      trigger={
        <>
          <Icon name="list-filter" />
          <span>Filtruj</span>
          {activeCount > 0 ? (
            <span
              className="tasks-project-query-count"
              aria-label={`Aktywne filtry: ${activeCount}`}
            >
              {activeCount}
            </span>
          ) : null}
          <Icon name="chevron-down" className="tasks-project-query-trigger__chevron" />
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
          <Icon name="chevron-down" className="tasks-project-query-trigger__chevron" />
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

export const DirectoryToolbar = forwardRef<
  HTMLFormElement,
  FormHTMLAttributes<HTMLFormElement> & ToolbarSlots
>(function DirectoryToolbar({ filters, actions, search, children, className = '', ...props }, ref) {
  return (
    <form
      {...props}
      ref={ref}
      className={`tasks-filterbar tasks-filterbar--directory work-item-toolbar app-toolbar ${className}`}
    >
      {children}
      <ToolbarContents filters={filters} actions={actions} search={search} />
    </form>
  );
});
