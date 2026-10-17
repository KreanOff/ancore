import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import type { Dashboard } from './types';
export function DashboardActions({
  item,
  busy,
  directory = false,
  favorite,
  remove,
}: {
  item: Dashboard;
  busy: boolean;
  directory?: boolean;
  favorite: () => void;
  remove: () => void;
}) {
  return (
    <Dropdown
      label={`Działania: ${item.name}`}
      className="documents-item-actions"
      triggerClassName={
        directory ? 'tasks-project-sheet__edit-button' : 'tasks-icon-button documents-icon-button'
      }
      menuClass="tasks-section-menu documents-item-menu"
      role="group"
      trigger={<Icon name={directory ? 'menu' : 'ellipsis'} />}
    >
      {(close) => (
        <div className="documents-menu-actions">
          {directory ? (
            <>
              <a className="tasks-project-menu-button" href={item.url}>
                <Icon name="layout-dashboard" />
                <span>Otwórz pulpit</span>
              </a>
              <button
                className="tasks-project-menu-button tasks-favorite-toggle"
                aria-pressed={item.favorite}
                disabled={busy}
                onClick={() => {
                  close();
                  favorite();
                }}
              >
                <Icon name={item.favorite ? 'star-filled' : 'star'} />
                <span>{item.favorite ? 'Usuń z ulubionych' : 'Dodaj do ulubionych'}</span>
              </button>
            </>
          ) : null}
          {item.editable ? (
            <>
              <a className="tasks-project-menu-button" href={item.gadgets_url}>
                <Icon name="layout-dashboard" />
                <span>Gadżety i układ</span>
              </a>
              <a className="tasks-project-menu-button" href={item.access_url}>
                <Icon name="users" />
                <span>Dostępy</span>
              </a>
              <a className="tasks-project-menu-button" href={item.edit_url}>
                <Icon name="settings" />
                <span>Ustawienia</span>
              </a>
              {!item.is_default ? (
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
            </>
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
