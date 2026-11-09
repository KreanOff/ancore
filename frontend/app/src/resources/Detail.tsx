import { Toolbar } from '../shared/DirectoryToolbar';
import { LoadMore } from '../shared/LoadMore';
import { PageHeader } from '../shared/PageHeader';
import { Icon } from '../shared/Icon';
import type { Overview, Resource, ResourceAction } from './types';

export const dateLabel = (value: string) => (value ? value.split('-').reverse().join('.') : '—');
const dateTime = (value: string) =>
  new Date(value).toLocaleString('pl-PL', { dateStyle: 'medium', timeStyle: 'short' });
const statusIcons: Record<string, string> = {
  available: 'circle-check',
  in_use: 'user-round',
  maintenance: 'wrench',
  retired: 'archive',
};

export function ResourceStatus({ resource }: { resource: Resource }) {
  return (
    <span className="tasks-project-value-badge resources-status">
      <Icon name={statusIcons[resource.status] || 'circle'} />
      {resource.status_label}
    </span>
  );
}

export function ResourceDetail({
  data,
  readOnly,
  busy,
  back,
  edit,
  operate,
  loadHistory,
  historyError,
  refresh,
}: {
  data: Overview;
  readOnly: boolean;
  busy: boolean;
  back: () => void;
  edit: () => void;
  operate: (action: ResourceAction) => void;
  loadHistory: () => void;
  historyError: string;
  refresh: () => void;
}) {
  const resource = data.resource;
  const fields = [
    ['Typ', resource.kind_label],
    ['Status', <ResourceStatus resource={resource} />],
    ['Numer ewidencyjny', resource.inventory_number],
    ['Numer seryjny', resource.serial_number],
    ['Osoba odpowiedzialna', resource.assignee_name],
    ['Lokalizacja', resource.location],
    ['Data zakupu', dateLabel(resource.purchased_on)],
    ['Ważność / gwarancja', dateLabel(resource.expires_on)],
    ['Planowany zwrot', dateLabel(resource.return_due_on)],
    ['Ostatnia zmiana', dateTime(resource.updated_at)],
  ] as const;
  return (
    <>
      <PageHeader
        className="resources-detail-header"
        heading={
          <>
            <button
              type="button"
              className="tasks-issue-close"
              onClick={back}
              aria-label="Wróć do zasobów"
            >
              <Icon name="arrow-left" />
            </button>
            <h1 className="tasks-topbar-title" title={resource.name} tabIndex={-1}>
              {resource.name}
            </h1>
          </>
        }
        actions={
          !readOnly ? (
            <>
              <button
                type="button"
                className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
                disabled={busy}
                onClick={edit}
              >
                <Icon name="pencil" />
                Edytuj zasób
              </button>
            </>
          ) : undefined
        }
      />
      <Toolbar
        className="resources-detail-actions"
        filters={
          <span className="resources-detail-caption">
            Karta zasobu{resource.inventory_number ? ` · ${resource.inventory_number}` : ''}
          </span>
        }
        actions={
          <>
            <button
              type="button"
              className="tasks-filter-button"
              disabled={busy}
              onClick={refresh}
              aria-label="Odśwież zasób"
              title="Odśwież zasób"
            >
              <Icon name="rotate-ccw" />
            </button>
            {!readOnly ? (
              <>
                {['available', 'in_use'].includes(resource.status) ? (
                  <button
                    className="tasks-filter-button"
                    disabled={busy}
                    onClick={() => operate('handover')}
                  >
                    <Icon name="user-round" />
                    Przekaż
                  </button>
                ) : null}
                {resource.status === 'in_use' ? (
                  <button
                    className="tasks-filter-button"
                    disabled={busy}
                    onClick={() => operate('return')}
                  >
                    <Icon name="rotate-ccw" />
                    Przyjmij zwrot
                  </button>
                ) : null}
                <button
                  className="tasks-filter-button"
                  disabled={busy}
                  onClick={() => operate('status')}
                >
                  <Icon name="circle-check" />
                  Zmień status
                </button>
                <button
                  className="tasks-filter-button"
                  disabled={busy}
                  onClick={() => operate('note')}
                >
                  <Icon name="plus" />
                  Dodaj notatkę
                </button>
              </>
            ) : null}
          </>
        }
      />
      <div className="resources-detail-content">
        {resource.overdue || resource.expiring_soon || resource.return_overdue ? (
          <div className="resources-deadline-notice" role="status">
            <Icon name="calendar-clock" />
            <div>
              {resource.overdue ? (
                <p>Termin ważności lub gwarancji minął {dateLabel(resource.expires_on)}.</p>
              ) : resource.expiring_soon ? (
                <p>
                  Termin ważności lub gwarancji upływa {dateLabel(resource.expires_on)} — w ciągu
                  najbliższych 30 dni.
                </p>
              ) : null}
              {resource.return_overdue ? (
                <p>
                  Planowany zwrot był {dateLabel(resource.return_due_on)}. Zasób nadal jest w
                  użyciu.
                </p>
              ) : null}
            </div>
          </div>
        ) : null}
        <div className="resources-detail-grid">
          <section className="resources-detail-panel" aria-label="Dane zasobu">
            <h2>Dane zasobu</h2>
            <dl className="resources-properties">
              {fields.map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value || '—'}</dd>
                </div>
              ))}
            </dl>
            <h2>Notatki</h2>
            <p className="resources-note-text">{resource.notes || 'Brak notatek.'}</p>
            <p className="resources-detail-caption">Dodano {dateTime(resource.created_at)}</p>
          </section>
          <section className="resources-detail-panel" aria-label="Historia zasobu">
            <h2>
              Historia <span className="resources-detail-caption">({data.history_total})</span>
            </h2>
            {data.history.length ? (
              <ol className="resources-history">
                {data.history.map((entry) => (
                  <li key={entry.id}>
                    <div className="resources-history-heading">
                      <span>{entry.label}</span>
                      <time dateTime={entry.created_at}>{dateTime(entry.created_at)}</time>
                    </div>
                    <p className="resources-detail-caption">{entry.actor}</p>
                    {entry.changes.length ? (
                      <dl className="resources-history-changes">
                        {entry.changes.map((change) => (
                          <div key={change.field}>
                            <dt>{change.label}</dt>
                            <dd>
                              <span>{change.before || '—'}</span>
                              <Icon name="arrow-right" />
                              <span>{change.after || '—'}</span>
                            </dd>
                          </div>
                        ))}
                      </dl>
                    ) : null}
                    {entry.note ? <p className="resources-note-text">{entry.note}</p> : null}
                  </li>
                ))}
              </ol>
            ) : (
              <p className="resources-detail-caption">
                Brak zarejestrowanych zmian. Historia będzie zapisywana od kolejnej operacji.
              </p>
            )}
            <LoadMore
              loaded={data.history.length}
              total={data.history_total}
              hasMore={!!data.history_next}
              loading={busy}
              error={historyError}
              onLoad={loadHistory}
              label="wpisy"
            />
          </section>
        </div>
      </div>
    </>
  );
}
