import { useCallback, useEffect, useRef, useState } from 'react';
import { EmbeddedForm } from '../forms/FormDialog';
import { Icon } from '../shared/Icon';
import { Modal } from '../shared/Modal';
import { errorMessage } from '../shared/api';
import { type Page, type PageProps, navigate, pageRequest } from '../shared/page';
import { DashboardView } from './DetailPage';
import type { DetailData, EditData, SettingsTab } from './types';

export default function SettingsDialog({
  initial,
  csrfToken,
  onClose,
  hostId,
}: PageProps & { onClose: (changed: boolean) => void; hostId?: string }) {
  const initialData = initial.data as DetailData | EditData;
  const [tab, setTab] = useState<SettingsTab>(
    initial.type === 'pulpit-edit' ? (initialData as EditData).section : 'gadgets',
  );
  const [pages, setPages] = useState<Partial<Record<SettingsTab, Page>>>(() => ({
    [tab]: initial,
  }));
  const [states, setStates] = useState<
    Partial<Record<SettingsTab, { dirty: boolean; pending: boolean }>>
  >({});
  const [error, setError] = useState(''),
    [notice, setNotice] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [life] = useState(() => new AbortController());
  const changed = useRef(false);
  const reportChanged = useCallback(() => {
    changed.current = true;
  }, []);
  const tabs = initialData.settings_tabs;
  const dirty = Object.values(states).some((state) => state?.dirty);
  const pending = Object.values(states).some((state) => state?.pending);
  useEffect(() => () => life.abort(), [life]);
  useEffect(() => {
    if (pages[tab]) return;
    let current = true;
    setError('');
    pageRequest<Page>(
      initial.api_url,
      tabs.find((item) => item.key === tab)!.url,
      csrfToken,
      life.signal,
    )
      .then((page) => {
        if (current) setPages((previous) => ({ ...previous, [tab]: page }));
      })
      .catch((exception) => {
        if (current && !life.signal.aborted) setError(errorMessage(exception));
      });
    return () => {
      current = false;
    };
  }, [tab, pages, tabs, initial.api_url, csrfToken, life, attempt]);
  const reportSettings = useCallback((dirty: boolean, pending: boolean) => {
    setStates((previous) => ({ ...previous, settings: { dirty, pending } }));
    if (dirty || pending) setNotice('');
  }, []);
  const reportAccess = useCallback((dirty: boolean, pending: boolean) => {
    setStates((previous) => ({ ...previous, access: { dirty, pending } }));
    if (dirty || pending) setNotice('');
  }, []);
  const reportGadgets = useCallback((pending: boolean) => {
    setStates((previous) => ({ ...previous, gadgets: { dirty: false, pending } }));
  }, []);
  function saved() {
    changed.current = true;
    // Settings and sharing also increment the dashboard revision used by the canvas.
    setPages((previous) => ({ ...previous, gadgets: undefined }));
    setNotice('Zmiany zostały zapisane.');
  }
  function closeFrom(element: HTMLElement) {
    const modal = element.closest<HTMLElement>('.tasks-modal');
    if (modal) window.AncoreTaskModals?.close(modal);
  }
  return (
    <Modal
      title="Ustawienia pulpitu"
      className="work-modal pulpit-settings-modal"
      dirty={dirty}
      pending={pending}
      onClose={() => onClose(changed.current)}
      hostId={hostId}
    >
      <div
        className="notifications-tabs pulpit-settings-tabs"
        role="tablist"
        aria-label="Ustawienia pulpitu"
        onKeyDown={(event) => {
          const index = tabs.findIndex((item) => item.key === tab);
          const next =
            event.key === 'Home'
              ? 0
              : event.key === 'End'
                ? tabs.length - 1
                : event.key === 'ArrowRight'
                  ? (index + 1) % tabs.length
                  : event.key === 'ArrowLeft'
                    ? (index + tabs.length - 1) % tabs.length
                    : -1;
          if (next < 0 || pending) return;
          event.preventDefault();
          setTab(tabs[next].key);
          setError('');
          setNotice('');
          event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus();
        }}
      >
        {tabs.map((item) => (
          <button
            key={item.key}
            type="button"
            id={`pulpit-settings-tab-${item.key}`}
            role="tab"
            aria-selected={tab === item.key}
            aria-controls={`pulpit-settings-panel-${item.key}`}
            tabIndex={tab === item.key ? 0 : -1}
            disabled={pending}
            onClick={() => {
              setTab(item.key);
              setError('');
              setNotice('');
            }}
          >
            <Icon name={item.icon} />
            {item.label}
          </button>
        ))}
      </div>
      {error ? (
        <div className="tasks-modal__errors pulpit-settings-message" role="alert">
          {error}
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setAttempt((value) => value + 1)}
          >
            Spróbuj ponownie
          </button>
        </div>
      ) : null}
      {notice ? (
        <p className="pulpit-settings-message" role="status">
          {notice}
        </p>
      ) : null}
      {!pages[tab] && !error ? (
        <p className="pulpit-settings-message" role="status">
          Wczytywanie ustawień…
        </p>
      ) : null}
      {tabs.map((item) => {
        const page = pages[item.key];
        const data = page?.data as EditData | undefined;
        return (
          <section
            key={item.key}
            id={`pulpit-settings-panel-${item.key}`}
            role="tabpanel"
            aria-labelledby={`pulpit-settings-tab-${item.key}`}
            hidden={tab !== item.key}
            className="pulpit-settings-panel"
          >
            {page && item.key === 'gadgets' ? (
              <>
                <DashboardView
                  initial={page}
                  csrfToken={csrfToken}
                  embedded
                  hostId={hostId}
                  onStateChange={reportGadgets}
                  onChanged={reportChanged}
                />
                <footer className="tasks-modal__footer">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    disabled={pending}
                    onClick={(event) => closeFrom(event.currentTarget)}
                  >
                    Gotowe
                  </button>
                </footer>
              </>
            ) : page && data ? (
              <EmbeddedForm
                data={{
                  title: item.label,
                  action: data.action,
                  return_url: data.return_url,
                  form: data.form,
                }}
                api={initial.api_url}
                csrfToken={csrfToken}
                onSaved={saved}
                onStateChange={item.key === 'settings' ? reportSettings : reportAccess}
              />
            ) : null}
          </section>
        );
      })}
    </Modal>
  );
}

export function SettingsPage({ initial, csrfToken }: PageProps) {
  const data = initial.data as DetailData | EditData;
  const [preview, setPreview] = useState<Page>();
  useEffect(() => {
    const controller = new AbortController();
    pageRequest<Page>(initial.api_url, data.dashboard.url, csrfToken, controller.signal)
      .then(setPreview)
      .catch(() => {
        /* The editor remains usable if its background cannot load. */
      });
    return () => controller.abort();
  }, [initial.api_url, data.dashboard.url, csrfToken]);
  return (
    <>
      {preview ? (
        <DashboardView initial={preview} csrfToken={csrfToken} />
      ) : (
        <div className="tasks-page work-page" />
      )}
      <SettingsDialog
        initial={initial}
        csrfToken={csrfToken}
        onClose={() => void navigate(data.return_url)}
      />
    </>
  );
}
