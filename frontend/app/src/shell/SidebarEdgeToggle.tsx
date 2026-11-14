import type { MouseEventHandler } from 'react';
import { Icon } from '../shared/Icon';

export default function SidebarEdgeToggle({
  side,
  label,
  expanded,
  onClick,
}: {
  side: 'left' | 'right';
  label: string;
  expanded: boolean;
  onClick: MouseEventHandler<HTMLButtonElement>;
}) {
  return (
    <button
      type="button"
      className={`sidebar-edge-toggle ${side}-sidebar-edge-toggle`}
      aria-label={label}
      title={label}
      aria-controls={side === 'left' ? 'app-sidebar' : 'app-right-sidebar'}
      aria-expanded={expanded}
      data-sidebar-collapse-toggle={side === 'left' ? '' : undefined}
      data-right-sidebar-toggle={side === 'right' ? '' : undefined}
      onClick={onClick}
    >
      <Icon name="chevron-right" className="sidebar-edge-toggle__arrow" />
    </button>
  );
}
