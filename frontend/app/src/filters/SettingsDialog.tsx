import { useCallback, useRef, useState } from 'react';
import { EmbeddedForm, type FormDialogData, type FormSection } from '../forms/FormDialog';
import { Icon } from '../shared/Icon';
import { Modal } from '../shared/Modal';

const sections: (FormSection & { icon: string })[] = [
  {
    id: 'filter-settings-main',
    label: 'Główna',
    icon: 'settings',
    fields: ['name', 'description', 'query'],
  },
  {
    id: 'filter-settings-access',
    label: 'Dostępy',
    icon: 'users',
    fields: ['visibility', 'shared_with'],
  },
];

export default function SettingsDialog({
  data,
  api,
  csrfToken,
  onClose,
  onSaved,
  hostId,
}: {
  data: FormDialogData;
  api: string;
  csrfToken: string;
  onClose: () => void;
  onSaved: (url: string) => void;
  hostId?: string;
}) {
  const [tab, setTab] = useState(sections[0].id);
  const [state, setState] = useState({ dirty: data.form.bound, pending: false });
  const [notice, setNotice] = useState('');
  const savedUrl = useRef('');
  const report = useCallback((dirty: boolean, pending: boolean) => {
    setState({ dirty, pending });
    if (dirty || pending) setNotice('');
  }, []);
  return (
    <Modal
      title={data.title}
      className="work-modal filter-settings-modal"
      hostId={hostId}
      dirty={state.dirty}
      pending={state.pending}
      onClose={() => (savedUrl.current ? onSaved(savedUrl.current) : onClose())}
    >
      <div
        className="notifications-tabs filter-settings-tabs"
        role="tablist"
        aria-label={data.title}
        onKeyDown={(event) => {
          const index = sections.findIndex((section) => section.id === tab);
          const next =
            event.key === 'Home'
              ? 0
              : event.key === 'End'
                ? sections.length - 1
                : event.key === 'ArrowRight'
                  ? (index + 1) % sections.length
                  : event.key === 'ArrowLeft'
                    ? (index + sections.length - 1) % sections.length
                    : -1;
          if (next < 0 || state.pending) return;
          event.preventDefault();
          setTab(sections[next].id);
          event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus();
        }}
      >
        {sections.map((section) => (
          <button
            key={section.id}
            id={`${section.id}-tab`}
            type="button"
            role="tab"
            aria-selected={tab === section.id}
            aria-controls={`${section.id}-panel`}
            tabIndex={tab === section.id ? 0 : -1}
            disabled={state.pending}
            onClick={() => setTab(section.id)}
          >
            <Icon name={section.icon} />
            {section.label}
          </button>
        ))}
      </div>
      {notice ? (
        <p className="filter-settings-message" role="status">
          {notice}
        </p>
      ) : null}
      <EmbeddedForm
        data={data}
        api={api}
        csrfToken={csrfToken}
        sections={sections}
        activeSection={tab}
        onInvalidSection={setTab}
        onStateChange={report}
        onSaved={(url) => {
          if (data.filter_settings === 'create') {
            return onSaved(url);
          }
          savedUrl.current = url;
          setNotice('Zmiany zostały zapisane.');
        }}
      />
    </Modal>
  );
}
