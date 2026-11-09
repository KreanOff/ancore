import type { ReactNode } from 'react';
import { Avatar } from './Avatar';
import { LocalDirectoryTable } from './LocalDirectoryTable';
import type { MemberRow } from './Members';
import { dateLabel } from '../spaces/types';

const columns = [
  { key: 'person', label: 'Nazwa', icon: 'users', width: 250 },
  { key: 'email', label: 'E-mail', icon: 'mail', width: 320 },
  { key: 'role', label: 'Rola', icon: 'user-round', width: 160, filterable: true },
  { key: 'joined', label: 'Dołączono', icon: 'calendar-days', width: 150 },
];

export function MemberDirectory({
  members,
  busy,
  selected,
  onSelect,
  controls,
  children,
}: {
  controls?: ReactNode;
  children?: ReactNode;
  members: MemberRow[];
  busy: boolean;
  selected: Set<number | string>;
  onSelect: (next: Set<number | string>) => void;
}) {
  return (
    <LocalDirectoryTable
      columns={columns}
      segment="space-settings-members"
      label="Członkowie przestrzeni"
      searchLabel="Szukaj osób"
      emptyLabel="Brak członków."
      busy={busy}
      selected={selected}
      onSelect={onSelect}
      controls={controls}
      rows={members.map((member) => ({
        id: member.id,
        label: member.name,
        sortValues: { joined: member.created_at || '' },
        values: {
          person: member.name,
          email: member.email,
          role: member.role_label,
          joined: dateLabel(member.created_at) || '—',
        },
        cells: {
          person: (
            <>
              <Avatar data={member.avatar} className="tasks-directory-avatar" />
              <span className="workplace-team__name">{member.name}</span>
            </>
          ),
        },
      }))}
    >
      {children}
    </LocalDirectoryTable>
  );
}
