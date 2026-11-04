import { FormDialog } from '../forms/FormDialog';
import { Avatar, type AvatarData } from '../shared/Avatar';
import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import { EmptyState } from '../shared/EmptyState';
import { Pagination, type PaginationData } from '../shared/Pagination';
import { Select } from '../shared/Select';
import { StatusGroup } from '../shared/StatusGroup';
import { usePageActions } from '../shared/usePageActions';
import { type PageProps, navigate } from '../shared/page';
import { ForYouTaskRow } from '../dashboard/ForYouPage';
import type { Item } from './types';
import type { Space } from './DirectoryPage';
interface Team {
  id: number;
  name: string;
  description: string;
  photo_url: string;
  url: string;
  member_count: number;
  space_count: number;
}
interface DirectoryTeam extends Team {
  open_count: number;
  is_member: boolean;
  is_admin: boolean;
}
interface Tab {
  key: string;
  label: string;
  url: string;
  count?: number | null;
}
interface Directory {
  url: string;
  query: string;
  tab: string;
  sort: string;
  tabs: Tab[];
  create_url: string;
  teams: DirectoryTeam[];
  pagination: PaginationData;
}
interface Member {
  id: number;
  name: string;
  email: string;
  avatar: AvatarData;
  role: string;
  role_label: string;
  can_change: boolean;
  edit_url: string;
  remove_url: string;
}
interface Detail extends Team {
  directory_url: string;
  edit_url: string;
  delete_url: string;
  member_url: string;
  can_manage: boolean;
  view: string;
  query: string;
  scope: string;
  role_filter: string;
  assignee_filter: string;
  tabs: Tab[];
  spaces: Space[];
  members: Member[];
  items: (Item & { space_name: string })[];
  counts: Record<string, number>;
  workload: { name: string; count: number; overdue: number; url: string }[];
  progress: number;
  pagination: PaginationData | null;
}
const sortOptions: [string, string][] = [
  ['name', 'Nazwa A–Z'],
  ['newest', 'Najnowsze'],
  ['members', 'Liczba członków'],
];
const scopeOptions: [string, string][] = [
  ['all', 'Wszystkie zadania'],
  ['open', 'Otwarte'],
  ['overdue', 'Po terminie'],
  ['due', 'Termin do 7 dni'],
  ['blocked', 'Zablokowane'],
  ['unassigned', 'Otwarte bez wykonawcy'],
  ['closed', 'Zamknięte'],
];
const roleOptions: [string, string][] = [
  ['', 'Wszystkie role'],
  ['admin', 'Administratorzy'],
  ['member', 'Członkowie'],
];
const assigneeOptions: [string, string][] = [
  ['', 'Wszyscy wykonawcy'],
  ['me', 'Przypisane do mnie'],
  ['unassigned', 'Bez wykonawcy'],
];

function Symbol({ team }: { team: Team }) {
  return (
    <span className="work-symbol">
      {team.photo_url ? <img src={team.photo_url} alt="" /> : <Icon name="users" />}
    </span>
  );
}
function Tasks({ items }: { items: Detail['items'] }) {
  const groups = new Map<string, Detail['items']>();
  for (const item of [...items].sort((a, b) => a.status_order - b.status_order)) {
    const key = `${item.category}:${item.status_label}:${item.status_color || ''}`;
    const group = groups.get(key);
    if (group) group.push(item);
    else groups.set(key, [item]);
  }
  if (!items.length)
    return (
      <EmptyState
        illustration="tasks"
        title="Brak zadań w tym widoku"
        description="Zadania pojawią się po przypisaniu do zespołu. Jeśli korzystasz z filtrów, zmień ich zakres."
      />
    );
  return (
    <div className="tasks-table-wrap tasks-board work-item-list">
      {[...groups].map(([key, rows]) => (
        <StatusGroup
          key={key}
          label={rows[0].status_label}
          category={rows[0].category}
          color={rows[0].status_color}
          count={rows.length}
        >
          <div className="tasks-issue-list">
            {rows.map((item) => (
              <ForYouTaskRow
                key={item.id}
                row={{
                  title: item.title,
                  url: item.url,
                  location: item.space_name,
                  icon: item.type_icon,
                  is_task: true,
                  key: item.key,
                  status_label: item.status_label,
                  overdue: item.due_urgency === 'overdue',
                  due_at: item.due_at || undefined,
                  task: {
                    status: item.category,
                    priority: item.priority,
                    priority_label: item.priority_label,
                    type_label: item.type_label,
                    type_icon: item.type_icon,
                    type_color: item.type_color,
                    tags_count: item.tags_count,
                    attachments_count: item.attachments_count,
                    due_urgency: item.due_urgency,
                  },
                }}
              />
            ))}
          </div>
        </StatusGroup>
      ))}
    </div>
  );
}
function TeamMembers({
  members,
  busy,
  open,
  remove,
}: {
  members: Member[];
  busy: boolean;
  open: (url: string) => Promise<void>;
  remove: (member: Member) => void;
}) {
  if (!members.length)
    return (
      <EmptyState
        illustration="people"
        title="Brak osób w tym widoku"
        description="Zmień filtry lub dodaj osobę z tego Workspace do zespołu."
      />
    );
  return (
    <div
      className="tasks-table-wrap tasks-board tasks-directory-board tasks-directory-sheet tasks-project-sheet workplace-team-sheet team-members-sheet"
      role="region"
      aria-label="Członkowie zespołu"
      tabIndex={0}
    >
      <section className="tasks-directory-group" role="table" aria-label="Lista członków">
        <div
          className="tasks-directory-header tasks-directory-sheet__header tasks-project-sheet__header"
          role="row"
        >
          {[
            ['action', 'Działania'],
            ['person', 'Osoba'],
            ['email', 'E-mail'],
            ['role', 'Rola'],
          ].map(([key, label]) => (
            <span
              key={key}
              className="tasks-directory-sheet__cell tasks-project-sheet__cell"
              data-column={key}
              role="columnheader"
              aria-label={key === 'action' ? label : undefined}
            >
              {key === 'action' ? null : label}
            </span>
          ))}
        </div>
        <div className="tasks-issue-list tasks-directory-list" role="rowgroup">
          {members.map((member) => (
            <div
              className="tasks-issue-row tasks-directory-row tasks-directory-sheet__row tasks-project-sheet__row"
              role="row"
              key={member.id}
            >
              <div className="tasks-directory-sheet__cell" data-column="action" role="cell">
                {member.can_change ? (
                  <Dropdown
                    searchable={false}
                    label={`Działania: ${member.name}`}
                    menuClass="documents-item-menu"
                    trigger={<Icon name="menu" />}
                  >
                    {(close) => (
                      <div className="documents-menu-actions">
                        <button
                          type="button"
                          role="menuitem"
                          className="tasks-project-menu-button"
                          disabled={busy}
                          onClick={() => {
                            close();
                            void open(member.edit_url);
                          }}
                        >
                          <Icon name="pencil" />
                          Zmień rolę
                        </button>
                        <button
                          type="button"
                          role="menuitem"
                          className="tasks-project-menu-button"
                          disabled={busy}
                          onClick={() => {
                            close();
                            remove(member);
                          }}
                        >
                          <Icon name="user-minus" />
                          Usuń z zespołu
                        </button>
                      </div>
                    )}
                  </Dropdown>
                ) : (
                  <span
                    title={
                      member.role === 'admin'
                        ? 'Zarządzanie wymaga uprawnień i co najmniej jednego aktywnego administratora.'
                        : undefined
                    }
                  >
                    —
                  </span>
                )}
              </div>
              <span className="tasks-directory-sheet__cell" data-column="person" role="cell">
                <Avatar data={member.avatar} className="tasks-directory-avatar" />
                <span className="workplace-team__name">{member.name}</span>
              </span>
              <span className="tasks-directory-sheet__cell" data-column="email" role="cell">
                <a href={`mailto:${member.email}`}>{member.email}</a>
              </span>
              <span className="tasks-directory-sheet__cell" data-column="role" role="cell">
                {member.role_label}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export default function TeamsPage(props: PageProps) {
  const { initial, csrfToken } = props,
    a = usePageActions(props),
    directory = initial.type === 'teams',
    d = initial.data as Directory,
    t = initial.data as Detail;
  const data = directory ? d : t;
  function filter(key: string, value: string) {
    const url = new URL(initial.url, location.origin);
    url.searchParams.delete('page');
    if (value) url.searchParams.set(key, value);
    else url.searchParams.delete(key);
    void navigate(url.pathname + url.search);
  }
  function remove(member: Member) {
    window.showConfirmModal({
      title: 'Usunąć osobę z zespołu?',
      message: `${member.name} przestanie należeć do tego zespołu. Dostęp do Workspace i przestrzeni oraz przypisane zadania pozostaną bez zmian.`,
      confirmText: 'Usuń z zespołu',
      cancelText: 'Anuluj',
      onConfirm: () => void a.act(member.remove_url, {}),
    });
  }
  const workUrl = (scope: string) => t.url + '?view=work&scope=' + scope;
  const filtered = directory
    ? !!d.query
    : !!(t.query || t.scope !== 'all' || t.role_filter || t.assignee_filter);
  return (
    <div
      className="tasks-page tasks-list-page work-page teams-page"
      data-react-screen={initial.type}
    >
      <section className="tasks-workspace" aria-busy={a.busy}>
        <header className="tasks-topbar tasks-topbar--directory tasks-topbar--project-directory">
          <div className="tasks-titlebar-left">
            {!directory ? (
              <a className="tasks-issue-close" href={t.directory_url} aria-label="Wróć do zespołów">
                <Icon name="arrow-left" />
              </a>
            ) : null}
            <h1 className="tasks-topbar-title">{initial.title}</h1>
          </div>
          <div className="tasks-titlebar-actions">
            {(directory ? !!d.create_url : t.can_manage) ? (
              <button
                type="button"
                className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
                disabled={a.busy}
                aria-haspopup="dialog"
                onClick={() => void a.open(directory ? d.create_url : t.edit_url)}
              >
                <Icon name={directory ? 'plus' : 'pencil'} />
                {directory ? 'Utwórz zespół' : 'Edytuj zespół'}
              </button>
            ) : null}
            {!directory && t.can_manage ? (
              <Dropdown
                searchable={false}
                label="Działania zespołu"
                trigger={<Icon name="menu" />}
                menuClass="documents-item-menu"
              >
                {(close) => (
                  <div className="documents-menu-actions">
                    <button
                      type="button"
                      role="menuitem"
                      className="tasks-project-menu-button"
                      disabled={a.busy}
                      onClick={() => {
                        close();
                        void a.open(t.delete_url);
                      }}
                    >
                      <Icon name="trash-2" />
                      Usuń zespół
                    </button>
                  </div>
                )}
              </Dropdown>
            ) : null}
          </div>
        </header>
        <nav
          className="notifications-tabs work-tabs"
          aria-label={directory ? 'Katalog zespołów' : 'Zespół'}
        >
          {data.tabs.map((tab) => (
            <a
              key={tab.key}
              href={tab.url}
              aria-current={tab.key === (directory ? d.tab : t.view) ? 'page' : undefined}
            >
              {tab.label}
              {tab.count != null ? <span className="work-caption">{tab.count}</span> : null}
            </a>
          ))}
        </nav>
        {a.error ? (
          <p className="tasks-modal__errors" role="alert">
            {a.error}
          </p>
        ) : null}
        <div className="work-content">
          {directory || t.view !== 'overview' ? (
            <form className="work-toolbar team-toolbar" method="get" action={data.url}>
              <input
                type="hidden"
                name={directory ? 'tab' : 'view'}
                value={directory ? d.tab : t.view}
              />
              <label className="tasks-search-field">
                <Icon name="search" />
                <input
                  type="search"
                  name="q"
                  defaultValue={data.query}
                  placeholder={
                    directory
                      ? 'Szukaj zespołu'
                      : t.view === 'members'
                        ? 'Szukaj osoby'
                        : t.view === 'spaces'
                          ? 'Szukaj przestrzeni'
                          : 'Szukaj zadania lub klucza'
                  }
                  aria-label={
                    directory
                      ? 'Szukaj zespołu'
                      : t.view === 'members'
                        ? 'Szukaj osoby'
                        : t.view === 'spaces'
                          ? 'Szukaj przestrzeni'
                          : 'Szukaj zadania lub klucza'
                  }
                />
              </label>
              {directory ? (
                <Select
                  hideLabel
                  label="Sortowanie zespołów"
                  name="sort"
                  value={d.sort}
                  options={sortOptions}
                  onChange={(value) => filter('sort', value)}
                />
              ) : null}
              {!directory && t.view === 'work' ? (
                <>
                  <Select
                    hideLabel
                    label="Zakres zadań"
                    name="scope"
                    value={t.scope}
                    options={scopeOptions}
                    onChange={(value) => filter('scope', value)}
                  />
                  <Select
                    hideLabel
                    label="Wykonawca"
                    name="assignee"
                    value={t.assignee_filter}
                    options={
                      /^\d+$/.test(t.assignee_filter)
                        ? [...assigneeOptions, [t.assignee_filter, 'Wybrana osoba']]
                        : assigneeOptions
                    }
                    onChange={(value) => filter('assignee', value)}
                  />
                </>
              ) : null}
              {!directory && t.view === 'members' ? (
                <Select
                  hideLabel
                  label="Rola w zespole"
                  name="role"
                  value={t.role_filter}
                  options={roleOptions}
                  onChange={(value) => filter('role', value)}
                />
              ) : null}
              <button className="btn btn-secondary" type="submit">
                Szukaj
              </button>
              {filtered ? (
                <a
                  className="btn btn-secondary"
                  href={directory ? d.url + '?tab=' + d.tab : t.url + '?view=' + t.view}
                >
                  Wyczyść filtry
                </a>
              ) : null}
              {!directory && t.can_manage && ['members', 'spaces'].includes(t.view) ? (
                <button
                  type="button"
                  className="btn btn-primary team-toolbar-action"
                  disabled={a.busy}
                  onClick={() => void a.open(t.view === 'members' ? t.member_url : t.edit_url)}
                >
                  <Icon name="plus" />
                  {t.view === 'members' ? 'Dodaj osobę' : 'Powiąż przestrzenie'}
                </button>
              ) : null}
            </form>
          ) : null}
          {directory ? (
            <div className="work-directory">
              {d.teams.length ? (
                d.teams.map((team) => (
                  <article className="work-space-card team-card" key={team.id}>
                    <div className="work-card-heading">
                      <Symbol team={team} />
                      {team.is_member ? (
                        <span className="work-caption">
                          {team.is_admin ? 'Administrator zespołu' : 'Twój zespół'}
                        </span>
                      ) : null}
                    </div>
                    <a className="work-card-title" href={team.url}>
                      {team.name}
                    </a>
                    <p>
                      {team.description.length > 160
                        ? team.description.slice(0, 159) + '…'
                        : team.description || 'Brak opisu zespołu.'}
                    </p>
                    <div className="work-card-footer team-card-counts">
                      <a href={team.url + '?view=members'}>
                        <Icon name="users" />
                        Osoby: {team.member_count}
                      </a>
                      <a href={team.url + '?view=work&scope=open'}>
                        <Icon name="list-checks" />
                        Otwarte: {team.open_count}
                      </a>
                      <a href={team.url + '?view=spaces'}>
                        <Icon name="layers" />
                        Przestrzenie: {team.space_count}
                      </a>
                    </div>
                  </article>
                ))
              ) : (
                <EmptyState
                  illustration="people"
                  title={
                    d.query
                      ? 'Nie znaleziono zespołów'
                      : d.tab === 'mine'
                        ? 'Nie należysz jeszcze do zespołu'
                        : d.tab === 'managed'
                          ? 'Nie zarządzasz żadnym zespołem'
                          : 'Brak zespołów'
                  }
                  description={
                    d.query
                      ? 'Zmień nazwę lub opis, których szukasz.'
                      : 'Zespoły łączą osoby, przestrzenie i wspólną pracę.'
                  }
                />
              )}
            </div>
          ) : (
            <>
              {t.view === 'overview' ? (
                <div className="work-overview">
                  <section className="work-panel team-profile">
                    <Symbol team={t} />
                    <div>
                      <h2>{t.name}</h2>
                      <p>
                        {t.description || 'Dodaj opis, aby przedstawić cel i zakres pracy zespołu.'}
                      </p>
                      <div className="team-profile-links">
                        <a href={t.url + '?view=members'}>Członkowie: {t.member_count}</a>
                        <a href={t.url + '?view=spaces'}>Powiązane przestrzenie: {t.space_count}</a>
                      </div>
                    </div>
                  </section>
                  <div className="work-metrics work-summary-metrics">
                    {[
                      ['open', 'Otwarte zadania', 'list-checks'],
                      ['overdue', 'Po terminie', 'clock-3'],
                      ['due', 'Termin do 7 dni', 'calendar-days'],
                      ['blocked', 'Zablokowane', 'lock'],
                    ].map(([key, label, icon]) => (
                      <a className="work-panel work-summary-metric" href={workUrl(key)} key={key}>
                        <span className="work-summary-metric-label">
                          <Icon name={icon} />
                          {label}
                        </span>
                        <strong>{t.counts[key]}</strong>
                      </a>
                    ))}
                  </div>
                  <div className="work-summary-grid">
                    <section className="work-panel">
                      <div className="work-panel-heading">
                        <h2>Postęp pracy</h2>
                        <a className="work-summary-link" href={workUrl('all')}>
                          Wszystkie zadania
                          <Icon name="arrow-right" />
                        </a>
                      </div>
                      <div className="team-progress-label">
                        <strong>{t.progress}%</strong>
                        <span>
                          Zamknięte: {t.counts.closed} z {t.counts.total}
                        </span>
                      </div>
                      <progress
                        className="team-progress"
                        max={100}
                        value={t.progress}
                        aria-label="Postęp pracy zespołu"
                      />
                      <div className="team-profile-links">
                        <a href={workUrl('unassigned')}>
                          Otwarte bez wykonawcy: {t.counts.unassigned}
                        </a>
                        <a href={workUrl('closed')}>Zamknięte: {t.counts.closed}</a>
                      </div>
                      <p className="work-caption">
                        Podsumowanie obejmuje zadania, do których masz dostęp.
                      </p>
                    </section>
                    <section className="work-panel">
                      <h2>Otwarte zadania według wykonawcy</h2>
                      {t.workload.length ? (
                        <div className="team-workload">
                          {t.workload.map((row) => (
                            <a href={row.url} key={row.url}>
                              <span>{row.name}</span>
                              <span>
                                {row.count}
                                {row.overdue ? <small> · po terminie: {row.overdue}</small> : null}
                              </span>
                            </a>
                          ))}
                        </div>
                      ) : (
                        <p>Brak otwartych zadań do rozdzielenia.</p>
                      )}
                    </section>
                  </div>
                  <section className="work-panel">
                    <div className="work-panel-heading">
                      <h2>Najbliższe zadania</h2>
                      <a className="work-summary-link" href={workUrl('open')}>
                        Zobacz wszystkie
                        <Icon name="arrow-right" />
                      </a>
                    </div>
                    <Tasks items={t.items} />
                  </section>
                </div>
              ) : null}
              {t.view === 'work' ? <Tasks items={t.items} /> : null}
              {t.view === 'members' ? (
                <>
                  <p className="workplace-team__hint">
                    Członkostwo w zespole organizuje współpracę. Dostęp do przestrzeni i zadań jest
                    nadawany osobno.
                  </p>
                  <TeamMembers members={t.members} busy={a.busy} open={a.open} remove={remove} />
                </>
              ) : null}
              {t.view === 'spaces' ? (
                <>
                  <p className="workplace-team__hint">
                    Widzisz tylko przestrzenie, do których masz dostęp.
                  </p>
                  <div className="work-directory">
                    {t.spaces.length ? (
                      t.spaces.map((space) => (
                        <article className="work-space-card" key={space.id}>
                          <Avatar space data={space.avatar} />
                          <a className="work-card-title" href={space.url}>
                            {space.name}
                          </a>
                          <span className="work-caption">
                            {space.key} · {space.kind_label}
                          </span>
                          <p>{space.description || 'Brak opisu przestrzeni.'}</p>
                        </article>
                      ))
                    ) : (
                      <EmptyState
                        illustration="spaces"
                        title="Brak powiązanych przestrzeni w tym widoku"
                        description="Powiąż dostępne przestrzenie w ustawieniach zespołu lub zmień wyszukiwanie."
                      />
                    )}
                  </div>
                </>
              ) : null}
            </>
          )}
        </div>
        <Pagination data={directory ? d.pagination : t.pagination} />
      </section>
      {a.modal ? (
        <FormDialog
          key={a.modal.action}
          data={a.modal}
          api={initial.api_url}
          csrfToken={csrfToken}
          onClose={a.close}
          onSaved={navigate}
        />
      ) : null}
    </div>
  );
}
