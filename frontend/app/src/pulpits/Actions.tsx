import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import type { Dashboard } from './types';
export function DashboardActions({
  item,
  busy,
  remove,
}: {
  item: Dashboard;
  busy: boolean;
  remove: () => void;
}) {
  return (
    <Dropdown
      label={`Działania: ${item.name}`}
      className="documents-item-actions"
      triggerClassName="tasks-icon-button documents-icon-button"
      menuClass="tasks-section-menu documents-item-menu"
      role="group"
      trigger={<Icon name="ellipsis" />}
    >
      {(close) => (
        <div className="documents-menu-actions">
          {item.editable ? (
            <>
              <a className="tasks-project-menu-button" href={item.gadgets_url}>
                <Icon name="layout-dashboard" />
                <span>Gadżety i układ</span>
              </a>
            </>
          ) : null}
          {item.manageable ? (
            <a className="tasks-project-menu-button" href={item.edit_url}>
              <Icon name="settings" />
              <span>Ustawienia</span>
            </a>
          ) : null}
          {item.deletable ? (
            <button
              className="tasks-project-menu-button"
              disabled={busy}
              onClick={() => {
                close();
                remove();
              }}
            >
              <Icon name="trash-2" />
              <span>Usuń pulpit</span>
            </button>
          ) : null}
        </div>
      )}
    </Dropdown>
  );
}
export function confirmDelete(title: string, name: string, action: () => void) {
  window.showConfirmModal({
    title,
    message: window.escapeHtmlForModal(`Usunąć „${name}”?`),
    confirmText: 'Usuń',
    cancelText: 'Anuluj',
    confirmClass: 'btn-danger',
    onConfirm: action,
  });
}
