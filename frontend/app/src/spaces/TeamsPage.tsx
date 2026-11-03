import { FormDialog } from '../forms/FormDialog';
import { Icon } from '../shared/Icon';
import { EmptyState } from '../shared/EmptyState';
import { Pagination, type PaginationData } from '../shared/Pagination';
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
}
interface Directory {
  url: string;
  query: string;
  tab: string;
  create_url: string;
  teams: Team[];
  pagination: PaginationData;
}
interface Detail extends Team {
  edit_url: string;
  member_url: string;
  can_manage: boolean;
  spaces: Space[];
  members: { id: number; name: string; role: string; remove_url: string }[];
  items: Item[];
  pagination: PaginationData;
}
export default function TeamsPage(props: PageProps) {
  const { initial, csrfToken } = props,
    a = usePageActions(props),
    directory = initial.type === 'teams',
    d = initial.data as Directory,
    t = initial.data as Detail;
  const groupKey = (item: Item) =>
    `${item.status_order}:${item.category}:${item.status_label}:${item.status_color || ''}`;
  const groups = directory
    ? []
    : [...new Set([...t.items].sort((a, b) => a.status_order - b.status_order).map(groupKey))].map(
        (key) => ({
          key,
          items: t.items.filter((item) => groupKey(item) === key),
        }),
      );
  return (
    <div className="tasks-page tasks-list-page work-page" data-react-screen={initial.type}>
      <section className="tasks-workspace" aria-busy={a.busy}>
        <header className="tasks-topbar tasks-topbar--directory tasks-topbar--project-directory">
          <div className="tasks-titlebar-left">
            {!directory ? (
              <a
                className="tasks-issue-close"
                href={t.url.replace(/\d+\/$/, '')}
                aria-label="Wróć do zespołów"
              >
                <Icon name="arrow-left" />
              </a>
            ) : null}
            <h1 className="tasks-topbar-title">{initial.title}</h1>
          </div>
          <div className="tasks-titlebar-actions">
            {(directory && d.create_url) || t.can_manage ? (
              <button
                type="button"
                className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
                disabled={a.busy}
                onClick={() => void a.open(directory ? d.create_url : t.edit_url)}
              >
                <Icon name={directory ? 'plus' : 'pencil'} />
                {directory ? 'Utwórz zespół' : 'Edytuj zespół'}
              </button>
            ) : null}
          </div>
        </header>
        {directory ? (
          <nav className="notifications-tabs work-tabs" aria-label="Katalog zespołów">
            <a href={d.url} aria-current={d.tab === 'all' ? 'page' : undefined}>
              Wszystkie zespoły
            </a>
            <a href={d.url + '?tab=mine'} aria-current={d.tab === 'mine' ? 'page' : undefined}>
              Moje zespoły
            </a>
          </nav>
        ) : null}
        {a.error ? (
          <p className="tasks-modal__errors" role="alert">
            {a.error}
          </p>
        ) : null}
        <div className="work-content">
          {directory ? (
            <>
              <form className="work-toolbar" method="get">
                <input type="hidden" name="tab" value={d.tab} />
                <label className="tasks-search-field">
                  <Icon name="search" />
                  <input
                    type="search"
                    name="q"
                    defaultValue={d.query}
                    placeholder="Szukaj zespołu"
                    aria-label="Szukaj zespołu"
                  />
                </label>
                <button className="btn btn-secondary" type="submit">
                  Szukaj
                </button>
              </form>
              <div className="work-directory">
                {d.teams.length ? (
                  d.teams.map((team) => (
                    <article className="work-space-card" key={team.id}>
                      <span className="work-symbol">
                        {team.photo_url ? (
                          <img src={team.photo_url} alt="" />
                        ) : (
                          <Icon name="users" />
                        )}
                      </span>
                      <a className="work-card-title" href={team.url}>
                        {team.name}
                      </a>
                      <p>
                        {team.description.length > 150
                          ? team.description.slice(0, 149) + '…'
                          : team.description || 'Poznaj zespół i jego pracę.'}
                      </p>
                      <div className="work-card-footer">{team.member_count} osób</div>
                    </article>
                  ))
                ) : (
                  <EmptyState
                    illustration="people"
                    title="Brak zespołów"
                    description={
                      d.query
                        ? 'Zmień wyszukiwaną nazwę.'
                        : 'Utwórz zespół, dodaj osoby i powiąż przestrzenie.'
                    }
                  />
                )}
              </div>
            </>
          ) : (
            <div className="work-overview">
              <section className="work-panel">
                <div className="work-panel-heading">
                  <span className="work-symbol">
                    {t.photo_url ? <img src={t.photo_url} alt="" /> : <Icon name="users" />}
                  </span>
                  <h2>{t.name}</h2>
                </div>
                <p style={{ whiteSpace: 'pre-wrap' }}>
                  {t.description || 'Zespół pracujący w tym Workspace.'}
                </p>
              </section>
              <section className="work-panel">
                <div className="work-panel-heading">
                  <h2>Członkowie zespołu</h2>
                  {t.can_manage ? (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      disabled={a.busy}
                      onClick={() => void a.open(t.member_url)}
                    >
                      Dodaj osobę / zmień rolę
                    </button>
                  ) : null}
                </div>
                {t.members.length ? (
                  t.members.map((member) => (
                    <div className="work-member" key={member.id}>
                      <span>{member.name}</span>
                      <span>{member.role}</span>
                      {t.can_manage ? (
                        <button
                          type="button"
                          className="btn btn-secondary"
                          disabled={a.busy}
                          onClick={() => void a.act(member.remove_url, {})}
                        >
                          Usuń z zespołu
                        </button>
                      ) : null}
                    </div>
                  ))
                ) : (
                  <p>Brak aktywnych członków.</p>
                )}
              </section>
              <section className="work-panel">
                <h2>Powiązane przestrzenie</h2>
                <div className="work-team-spaces">
                  {t.spaces.length ? (
                    t.spaces.map((space) => (
                      <a className="btn btn-secondary" href={space.url} key={space.id}>
                        {space.name} · {space.key}
                      </a>
                    ))
                  ) : (
                    <p>Brak dostępnych powiązanych przestrzeni.</p>
                  )}
                </div>
              </section>
              <section className="work-panel">
                <h2>Praca zespołu</h2>
                <div
                  className={`tasks-table-wrap tasks-board work-item-list ${t.items.length ? '' : 'tasks-board--empty'}`}
                >
                  {groups.length ? (
                    groups.map((group) => (
                      <StatusGroup
                        key={group.key}
                        label={group.items[0].status_label}
                        category={group.items[0].category}
                        color={group.items[0].status_color}
                        count={group.items.length}
                      >
                        <div className="tasks-issue-list">
                          {group.items.map((item) => (
                            <ForYouTaskRow
                              selectable
                              key={item.id}
                              row={{
                                title: item.title,
                                url: item.url,
                                location: initial.title,
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
                    ))
                  ) : (
                    <EmptyState
                      illustration="tasks"
                      title="Nie ma jeszcze zadań."
                      description="Nowe zadania pojawią się tutaj po ich utworzeniu."
                    />
                  )}
                </div>
              </section>
            </div>
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
