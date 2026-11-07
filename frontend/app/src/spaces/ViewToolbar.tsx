import type { ReactNode } from 'react';
import { Toolbar } from '../shared/DirectoryToolbar';

export function ViewToolbar({
  children,
  actions,
  search,
  className = '',
}: {
  children: ReactNode;
  actions?: ReactNode;
  search?: ReactNode;
  className?: string;
}) {
  return (
    <Toolbar
      className={`work-view-toolbar ${className}`}
      filters={children}
      actions={actions}
      search={search}
    />
  );
}
