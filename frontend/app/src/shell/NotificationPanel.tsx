import { Toolbar } from '../shared/DirectoryToolbar';
import { LoadMore } from '../shared/LoadMore';
import { Fragment, useEffect, useRef, useState, type MouseEvent } from 'react';
import { flushSync } from 'react-dom';
import { Avatar } from '../shared/Avatar';
import { Icon } from '../shared/Icon';
import { Modal } from '../shared/Modal';
import { navigate, pageRequest } from '../shared/page';
import { errorMessage } from '../shared/api';
import { LoadingRows, PanelState } from './States';
import WorkspaceSelect from './WorkspaceSelect';
import type { Inbox, NotificationItem, PanelsConfig, Summary } from './types';
const filters = [
  ['all', 'Wszystkie'],
  ['unread', 'Nieprzeczytane'],
  ['reminders', 'Przypomnienia'],
  ['mentions', 'Wzmianki'],
  ['following', 'Obserwowane'],
  ['archived', 'Archiwum'],
];
const empty: Record<string, [string, string]> = {
  all: [
    'Brak nowych powiadomień.',
    'Komentarze, wzmianki i przypomnienia pojawią się w tym miejscu.',
  ],
  unread: ['Wszystko przeczytane', 'Jesteś na bieżąco. Nowe powiadomienia pojawią się tutaj.'],
  reminders: [
    'Brak przypomnień',
    'Ustaw datę przypomnienia w zadaniu. Pojawi się tutaj o wybranej porze — dla wykonawcy, a bez wykonawcy dla właściciela Workspace.',
  ],
  mentions: [
    'Brak wzmianek',
    'Tutaj zobaczysz komentarze, w których ktoś wspomniał o Tobie przez @.',
  ],
  following: [
    'Brak nowych komentarzy w obserwowanych',
    'Nowe komentarze w obserwowanych elementach pojawią się tutaj.',
  ],
  archived: ['Archiwum jest puste', 'Zarchiwizowane powiadomienia pojawią się tutaj.'],
};
export default function NotificationPanel({
  config,
  token,
  summary,
  updateSummary,
  preferences,
  setPreferences,
  onClose,
}: {
  config: PanelsConfig;
  token: string;
  summary: Summary;
  updateSummary: (data: Summary) => void;
  onClose: () => void;
  preferences: { view: string; workspace: string };
  setPreferences: (value: { view: string; workspace: string }) => void;
}) {
  const view = preferences.view,
    workspace = preferences.workspace;
  const [workplaces, setWorkplaces] = useState<Inbox['workplaces']>([]);
  const [payload, setPayload] = useState<Inbox | null>(null),
    [loading, setLoading] = useState(true);
  const [mutating, setMutating] = useState(false),
    [error, setError] = useState(''),
    [status, setStatus] = useState('Pobieranie powiadomień…');
  const [loadFailed, setLoadFailed] = useState(false);
  const read = useRef<AbortController>(),
    mutation = useRef<AbortController>(),
    busy = useRef(false),
    alive = useRef(true);
  const content = useRef<HTMLDivElement>(null);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      read.current?.abort();
      mutation.current?.abort();
    };
  }, []);
  async function load({ append = false, quiet = false, focusKey = '' } = {}): Promise<boolean> {
    read.current?.abort();
    const controller = new AbortController();
    read.current = controller;
    setLoading(true);
    setError('');
    setLoadFailed(false);
    setStatus('Pobieranie powiadomień…');
    const scroll = content.current?.scrollTop || 0;
    if (!append && !quiet) setPayload(null);
    const params = new URLSearchParams({ view, workspace });
    if (append && payload?.next_cursor) params.set('cursor', payload.next_cursor);
    try {
      const data = await pageRequest<Inbox>(
        config.api_url,
        config.notifications_url + '?' + params,
        token,
        controller.signal,
      );
      if (controller.signal.aborted || !alive.current) return false;
      updateSummary(data);
      setWorkplaces(data.workplaces);
      setPayload((previous) =>
        append && previous ? { ...data, items: [...previous.items, ...data.items] } : data,
      );
      setStatus(`Powiadomienia: ${data.total}. Nieprzeczytane: ${data.filtered_unread_count}.`);
      requestAnimationFrame(() => {
        if (!alive.current || controller.signal.aborted) return;
        if (content.current) content.current.scrollTop = quiet || append ? scroll : 0;
        const key = focusKey || (append ? data.items[0]?.key : '');
        if (key) {
          const row = [
            ...(content.current?.querySelectorAll<HTMLElement>('[data-notification-key]') || []),
          ].find((item) => item.dataset.notificationKey === key);
          (
            row?.querySelector<HTMLElement>(
              append ? '.notification-card__link' : '.notification-card__actions button',
            ) || content.current
          )?.focus({ preventScroll: true });
        }
      });
      return true;
    } catch (e) {
      if (controller.signal.aborted || !alive.current) return false;
      setError(errorMessage(e));
      setLoadFailed(!quiet && !append);
      setStatus('Nie udało się pobrać powiadomień.');
      return false;
    } finally {
      if (read.current === controller && alive.current) setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, [view, workspace]);
  async function action(kind: string, key = '', url = '', snapshot = payload?.snapshot || '') {
    if (busy.current || !alive.current) return;
    busy.current = true;
    setMutating(true);
    setError('');
    read.current?.abort();
    const controller = new AbortController();
    mutation.current = controller;
    try {
      const result = await pageRequest<Summary>(
        config.api_url,
        config.action_url,
        token,
        controller.signal,
        { action: kind, key, snapshot },
      );
      if (controller.signal.aborted || !alive.current) return;
      updateSummary(result);
      if (url) {
        flushSync(onClose);
        void navigate(url);
        return;
      }
      const refreshed = await load({ quiet: true, focusKey: key });
      const message =
        (
          {
            archive: 'Powiadomienie przeniesione do archiwum.',
            restore: 'Powiadomienie przywrócone.',
            delete: 'Powiadomienie usunięte.',
            delete_all: 'Powiadomienia z wybranego widoku zostały usunięte.',
            read_all: 'Powiadomienia z wybranego widoku oznaczono jako przeczytane.',
          } as Record<string, string>
        )[kind] || 'Stan powiadomień zapisany.';
      if (refreshed) setStatus(message);
      if (['read_all', 'delete', 'delete_all'].includes(kind))
        window.showNotification?.(message, 'success');
    } catch (e) {
      if (!controller.signal.aborted && alive.current) {
        setError(errorMessage(e));
        setLoading(false);
      }
    } finally {
      busy.current = false;
      if (alive.current) setMutating(false);
    }
  }
  function confirm(kind: string, key = '') {
    if (busy.current || document.querySelector('.confirm-modal-overlay')) return;
    const snapshot = payload?.snapshot || '';
    window.showConfirmModal({
      title: kind === 'delete_all' ? 'Usunąć wszystkie powiadomienia?' : 'Usunąć powiadomienie?',
      message:
        (kind === 'delete_all'
          ? `Usuniesz powiadomienia z wybranego widoku (${payload?.deletable_count || 0}), również ze starszych stron. `
          : 'Usuniesz to powiadomienie ze swojej listy. ') +
        'Usuniętych powiadomień nie można przywrócić. Historia zadań pozostanie bez zmian.',
      confirmText: kind === 'delete_all' ? 'Usuń wszystkie' : 'Usuń',
      cancelText: 'Anuluj',
      onConfirm: () => void action(kind, key, '', snapshot),
    });
  }
  function openItem(event: MouseEvent<HTMLAnchorElement>, item: NotificationItem) {
    if (event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    void action('read', item.key, item.url);
  }
  const fresh =
    payload &&
    JSON.stringify([payload.revision, payload.unread_count]) !==
      JSON.stringify([summary.revision, summary.unread_count]);
  let previousGroup = '';
  return (
    <Modal
      id="notifications-panel"
      title="Powiadomienia"
      className="notifications-panel"
      hostId="app-global-modals"
      pending={mutating}
      onClose={onClose}
      footer={
        <footer className="tasks-modal__footer">
          <button type="button" className="btn btn-secondary" disabled={mutating} data-close-modal>
            Zamknij
          </button>
        </footer>
      }
    >
      <div
        className="tasks-modal__body notifications-panel__body"
        data-react-screen="notifications"
      >
        <div className="notifications-controls">
          <div className="notifications-tabs" role="group" aria-label="Filtr powiadomień">
            {filters.map(([key, label]) => (
              <button
                type="button"
                key={key}
                aria-pressed={view === key}
                disabled={mutating}
                onClick={() => setPreferences({ view: key, workspace })}
              >
                {label}
                {key === 'unread' ? <span>{summary.unread_count}</span> : null}
              </button>
            ))}
          </div>
          <Toolbar
            className="notifications-toolbar app-toolbar--embedded"
            filters={
              <WorkspaceSelect
                choices={workplaces}
                value={workspace}
                disabled={mutating}
                onChange={(value) => setPreferences({ view, workspace: value })}
              />
            }
            actions={
              <>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm tasks-filter-button"
                  disabled={loading || mutating || !payload?.filtered_unread_count}
                  title="Oznacz wszystkie powiadomienia z wybranego filtra jako przeczytane, również starsze"
                  onClick={() => void action('read_all')}
                >
                  <Icon name="check" />
                  <span>Oznacz wszystkie jako przeczytane</span>
                </button>
                <button
                  type="button"
                  className="tasks-icon-button"
                  disabled={loading || mutating || !payload?.deletable_count}
                  title="Usuń wszystkie powiadomienia z wybranego filtra"
                  aria-label="Usuń wszystkie powiadomienia z wybranego filtra"
                  onClick={() => confirm('delete_all')}
                >
                  <Icon name="trash-2" />
                </button>
                <button
                  type="button"
                  className="tasks-icon-button"
                  disabled={mutating}
                  title="Odśwież powiadomienia"
                  aria-label="Odśwież powiadomienia"
                  onClick={() => void load()}
                >
                  <Icon name="refresh-cw" />
                </button>
              </>
            }
          />
        </div>
        {fresh ? (
          <button
            type="button"
            className="notifications-new-items"
            disabled={mutating}
            onClick={() => void load()}
          >
            Są nowe powiadomienia — pokaż
          </button>
        ) : null}
        {error ? (
          <p className="notifications-error" role="alert">
            {error}
          </p>
        ) : null}
        <div
          className="notifications-panel__content"
          ref={content}
          tabIndex={-1}
          aria-busy={loading || mutating}
        >
          {!payload && loading ? (
            <LoadingRows />
          ) : loadFailed ? (
            <PanelState
              icon="wifi-off"
              title="Nie udało się pobrać powiadomień"
              retry={() => void load()}
            >
              Sprawdź połączenie i spróbuj ponownie.
            </PanelState>
          ) : !payload?.items.length ? (
            <div className="notifications-panel__empty">
              <PanelState
                icon={view === 'archived' ? 'archive' : 'bell-off'}
                title={empty[view][0]}
              >
                {empty[view][1]}
              </PanelState>
            </div>
          ) : (
            <div className="dashboard-notifications-list" role="list">
              {payload.items.map((item) => {
                const group = item.group_label !== previousGroup;
                previousGroup = item.group_label;
                return (
                  <Fragment key={item.key}>
                    {group ? (
                      <div className="notifications-group-label" role="presentation">
                        {item.group_label}
                      </div>
                    ) : null}
                    <article
                      className={'notification-card' + (!item.is_read ? ' is-unread' : '')}
                      role="listitem"
                      data-notification-key={item.key}
                    >
                      <Avatar data={item.actor_avatar} className="dashboard-notification-avatar" />
                      <div className="notification-card__body">
                        <div className="notification-card__meta">
                          <span>{item.event_label}</span>
                          <time dateTime={item.created_at} title={item.full_date}>
                            {item.time}
                          </time>
                          {!item.is_read ? (
                            <span className="notification-card__dot" title="Nieprzeczytane">
                              <span className="u-sr-only">Nieprzeczytane</span>
                            </span>
                          ) : null}
                        </div>
                        <a
                          href={item.url}
                          className="notification-card__link"
                          onClick={(event) => openItem(event, item)}
                        >
                          <span className="notification-card__actor">
                            {item.actor_label} {item.action_message}
                          </span>
                          <span className="notification-card__title">{item.title}</span>
                        </a>
                        {item.details.map((detail, index) => (
                          <div
                            key={index}
                            className={
                              'notification-card__detail' +
                              (detail.label === 'Komentarz'
                                ? ' notification-card__detail--comment'
                                : '')
                            }
                          >
                            {detail.label !== 'Komentarz' ? detail.label + ': ' : ''}
                            {detail.from_label ? detail.from_label + ' → ' : ''}
                            {detail.text}
                          </div>
                        ))}
                        <div className="notification-card__footer">
                          <span className="notification-card__location" title={item.location_label}>
                            {item.workplace_label}
                            {` · ${item.source_label} · #${item.object_id}`}
                          </span>
                        </div>
                        {item.action_label ? (
                          <a
                            href={item.url}
                            className="btn btn-primary btn-sm notification-card__decision"
                            onClick={(event) => openItem(event, item)}
                          >
                            {item.action_label}
                            <Icon name="arrow-right" />
                          </a>
                        ) : null}
                      </div>
                    </article>
                  </Fragment>
                );
              })}
            </div>
          )}
          {payload ? (
            <LoadMore
              loaded={payload.items.length}
              total={payload.total}
              hasMore={!!payload.next_cursor}
              loading={loading}
              disabled={mutating}
              onLoad={() => void load({ append: true })}
              label="Powiadomienia"
            />
          ) : null}
        </div>
      </div>
      <span className="u-sr-only" role="status" aria-live="polite" aria-atomic="true">
        {status}
      </span>
    </Modal>
  );
}
