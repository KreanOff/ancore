import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Icon } from '../shared/Icon';
import { pageRequest } from '../shared/page';
import Search from './Search';
import Sticker from './Sticker';
import NotificationPanel from './NotificationPanel';
import type { PanelsConfig, Summary } from './types';

export default function GlobalPanels({ config, token }: { config: PanelsConfig; token: string }) {
  const [open, setOpen] = useState(false);
  const [preferences, setPreferences] = useState({ view: 'all', workspace: '' });
  const [summary, setSummary] = useState<Summary>({
    unread_count: 0,
    pending_invitation_count: config.pending_invitation_count,
    revision: [],
  });
  const summaryRequest = useRef<AbortController>(),
    alive = useRef(true);
  const updateSummary = useCallback((data: Summary) => {
    summaryRequest.current?.abort();
    summaryRequest.current = undefined;
    if (alive.current)
      setSummary({
        unread_count: data.unread_count,
        pending_invitation_count: data.pending_invitation_count,
        revision: data.revision,
      });
  }, []);
  const refresh = useCallback(async () => {
    if (document.hidden || summaryRequest.current) return;
    const controller = new AbortController();
    summaryRequest.current = controller;
    try {
      const data = await pageRequest<Summary>(
        config.api_url,
        config.notifications_url + '?summary=1',
        token,
        controller.signal,
      );
      if (!controller.signal.aborted) setSummary(data);
    } catch {
      /* Keep the last known badge offline; the panel has an explicit retry. */
    } finally {
      if (summaryRequest.current === controller) summaryRequest.current = undefined;
    }
  }, [config.api_url, config.notifications_url, token]);
  useEffect(() => {
    alive.current = true;
    void refresh();
    const timer = setInterval(() => void refresh(), 30000);
    const visible = () => {
      if (!document.hidden) void refresh();
    };
    const close = () => setOpen(false);
    document.addEventListener('ancore:content-unloading', close);
    document.addEventListener('ancore:content-loaded', visible);
    document.addEventListener('visibilitychange', visible);
    window.addEventListener('pageshow', visible);
    window.addEventListener('online', visible);
    for (const name of [
      'ancore:global-search-open',
      'ancore:workspace-menu-open',
      'ancore:sidebar-toggle',
    ])
      window.addEventListener(name, close);
    return () => {
      alive.current = false;
      clearInterval(timer);
      summaryRequest.current?.abort();
      document.removeEventListener('ancore:content-unloading', close);
      document.removeEventListener('ancore:content-loaded', visible);
      document.removeEventListener('visibilitychange', visible);
      window.removeEventListener('pageshow', visible);
      window.removeEventListener('online', visible);
      for (const name of [
        'ancore:global-search-open',
        'ancore:workspace-menu-open',
        'ancore:sidebar-toggle',
      ])
        window.removeEventListener(name, close);
    };
  }, [refresh]);
  const label = `Nieprzeczytane: ${summary.unread_count}. Oczekujące zaproszenia: ${summary.pending_invitation_count}.`;
  return (
    <>
      <div id="app-global-modals" style={{ display: 'contents' }} />
      {createPortal(
        <Search config={config} token={token} />,
        document.getElementById('app-global-search-host')!,
      )}
      <Sticker user={config.user_id} />
      {createPortal(
        <button
          type="button"
          className="tasks-icon-button app-topbar__action"
          aria-label="Powiadomienia"
          aria-controls="notifications-panel"
          aria-expanded={open}
          aria-describedby="notifications-invitation-status"
          title={'Powiadomienia · ' + label}
          onClick={() => {
            if (!open) window.dispatchEvent(new CustomEvent('ancore:notifications-open'));
            setOpen(!open);
          }}
        >
          <Icon name="bell" />
          <span
            className="notifications-toggle__indicator"
            aria-hidden="true"
            hidden={!summary.unread_count || summary.pending_invitation_count > 0}
          />
          <span
            className="notifications-toggle__invitation-count"
            aria-hidden="true"
            hidden={!summary.pending_invitation_count}
          >
            {summary.pending_invitation_count > 9 ? '9+' : summary.pending_invitation_count}
          </span>
          <span id="notifications-invitation-status" className="u-sr-only">
            {label}
          </span>
        </button>,
        document.getElementById('app-global-actions-host')!,
      )}
      {open ? (
        <NotificationPanel
          config={config}
          token={token}
          summary={summary}
          updateSummary={updateSummary}
          preferences={preferences}
          setPreferences={setPreferences}
          onClose={() => setOpen(false)}
        />
      ) : null}
    </>
  );
}
