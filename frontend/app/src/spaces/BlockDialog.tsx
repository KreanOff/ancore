import { useEffect, useRef, useState } from 'react';
import { Modal } from '../shared/Modal';
import { Select } from '../shared/Select';
import { errorMessage } from '../shared/api';
import { pageRequest } from '../shared/page';
import type { Item } from './types';

export interface BlockDialogData {
  item: Item;
  block_responsible_options: { id: number; label: string }[];
}

export function BlockDialog({
  data,
  api,
  csrfToken,
  view,
  onClose,
  onRefresh,
}: {
  data: BlockDialogData;
  api: string;
  csrfToken: string;
  view: string;
  onClose: () => void;
  onRefresh: () => Promise<void>;
}) {
  const { item } = data;
  const initialReason = item.blocked?.reason || '';
  const initialResponsible = String(item.blocked?.responsible?.id ?? '');
  const [reason, setReason] = useState(initialReason);
  const [responsible, setResponsible] = useState(initialResponsible);
  const [busy, setBusy] = useState(false);
  const [committed, setCommitted] = useState(false);
  const [error, setError] = useState('');
  const pending = useRef(false);
  const saved = useRef(false);
  const life = useRef(new AbortController());
  useEffect(() => () => life.current.abort(), []);
  const options: [string, string][] = [
    ['', 'Wykonawca zadania (jeśli ma dostęp)'],
    ...data.block_responsible_options.map(({ id, label }): [string, string] => [String(id), label]),
  ];
  async function save(action: 'block' | 'unblock') {
    if (pending.current || (!saved.current && action === 'block' && !reason.trim())) return;
    pending.current = true;
    setBusy(true);
    setError('');
    try {
      if (!saved.current) {
        const form = new FormData();
        Object.entries({
          action,
          source_status: item.status,
          source_in_backlog: String(item.in_backlog),
          source_blocked_revision: String(item.blocked_revision ?? 0),
          blocked_reason: reason.trim(),
          blocked_responsible: responsible,
          return_view: view,
        }).forEach(([key, value]) => form.set(key, value));
        await pageRequest(api, item.action_url, csrfToken, life.current.signal, form);
        saved.current = true;
        setCommitted(true);
      }
      await onRefresh();
      if (!life.current.signal.aborted) onClose();
    } catch (exception) {
      if (!life.current.signal.aborted)
        setError(
          (saved.current ? 'Zmiana została zapisana. Odśwież widok, aby ją zobaczyć. ' : '') +
            errorMessage(exception),
        );
    } finally {
      pending.current = false;
      if (!life.current.signal.aborted) setBusy(false);
    }
  }
  return (
    <Modal
      title={`Blokada zadania ${item.key}`}
      size="compact"
      className="work-modal work-block-dialog"
      pending={busy || committed}
      dirty={!committed && (reason !== initialReason || responsible !== initialResponsible)}
      onClose={onClose}
    >
      <form
        className="tasks-modal__form"
        onSubmit={(event) => {
          event.preventDefault();
          void save('block');
        }}
      >
        <div className="tasks-modal__body">
          <p>{item.title}</p>
          {error ? (
            <div className="tasks-modal__errors" role="alert">
              {error}
            </div>
          ) : null}
          <fieldset className="work-block-fields" disabled={busy || committed}>
            <label className="documents-field tasks-form-field">
              Powód blokady
              <textarea
                className="form-input"
                value={reason}
                required
                maxLength={2000}
                rows={4}
                onChange={(event) => setReason(event.target.value)}
              />
            </label>
            <Select
              label="Osoba odpowiedzialna za usunięcie blokady"
              name="blocked_responsible"
              value={responsible}
              options={options}
              onChange={setResponsible}
            />
            <p className="work-caption">
              Blokada pozostawia zadanie w obecnym etapie i w limicie pracy w toku.
            </p>
          </fieldset>
        </div>
        <footer className="tasks-modal__footer">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={busy || committed}
            onClick={() => {
              const element = document.querySelector<HTMLElement>('.work-block-dialog');
              if (element) window.AncoreTaskModals?.close(element);
            }}
          >
            Anuluj
          </button>
          {item.blocked && !committed ? (
            <button
              type="button"
              className="btn btn-secondary"
              disabled={busy}
              onClick={() => void save('unblock')}
            >
              Usuń blokadę
            </button>
          ) : null}
          <button
            type="submit"
            className="tasks-modal__submit"
            disabled={busy || (!committed && !reason.trim())}
          >
            {busy
              ? 'Zapisywanie…'
              : committed
                ? 'Odśwież widok'
                : item.blocked
                  ? 'Zapisz blokadę'
                  : 'Zablokuj zadanie'}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
