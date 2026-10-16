import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import type { DirectoryData, Row } from './types';
export function RowActions({
  row,
  data,
  sheet,
  busy,
  open,
  act,
}: {
  row: Row;
  data: DirectoryData;
  sheet?: boolean;
  busy: boolean;
  open: (url: string) => void;
  act: (url: string, values: Record<string, string>) => void;
}) {
  const kind = row.row_kind,
    library = kind === 'library',
    folder = kind === 'folder';
  const button = (
    label: string,
    icon: string,
    url: string | undefined,
    values = data.return_values,
    confirm = false,
  ) =>
    url ? (
      <button
        type="button"
        className={
          'tasks-project-menu-button' + (icon === 'star' && row.starred ? ' is-starred' : '')
        }
        disabled={busy}
        aria-label={label}
        aria-pressed={icon === 'star' ? row.starred : undefined}
        onClick={() => {
          window.AncoreDropdownLayer?.dismiss();
          if (confirm)
            window.showConfirmModal({
              title: 'Potwierdź operację',
              message: 'Przenieść dokument do kosza? Możesz go później przywrócić.',
              confirmText: 'Potwierdź',
              cancelText: 'Anuluj',
              confirmClass: 'btn-primary',
              onConfirm: () => act(url, values),
            });
          else act(url, values);
        }}
      >
        <Icon name={icon} />
        <span>{label}</span>
      </button>
    ) : null;
  const modal = (label: string, icon: string, url?: string) =>
    url ? (
      <button
        type="button"
        className="tasks-project-menu-button"
        disabled={busy}
        onClick={() => {
          window.AncoreDropdownLayer?.dismiss();
          open(url);
        }}
      >
        <Icon name={icon} />
        <span>{label}</span>
      </button>
    ) : null;
  return (
    <Dropdown
      label={`Działania ${library ? 'dysku' : folder ? 'folderu' : 'pliku'}: ${row.name}`}
      className="documents-item-actions"
      role="group"
      menuClass="tasks-section-menu documents-item-menu"
      triggerClassName={
        sheet ? 'tasks-project-sheet__edit-button' : 'tasks-icon-button documents-icon-button'
      }
      trigger={<Icon name="menu" />}
    >
      {(close) => (
        <div
          className="documents-menu-actions"
          onClick={(event) => {
            if ((event.target as Element).closest('a')) close();
          }}
        >
          {library ? (
            <>
              {modal('Ustawienia dysku', 'pencil', row.edit_url)}
              {button('Usuń pusty dysk', 'trash-2', row.delete_url, {})}
              <a className="tasks-project-menu-button" href={row.url}>
                <Icon name="chevron-right" />
                <span>Otwórz dysk</span>
              </a>
            </>
          ) : data.view === 'trash' ? (
            button('Przywróć', 'rotate-ccw', row.restore_url)
          ) : (
            <>
              {!data.office ? modal('Przenieś do…', 'folder-input', row.move_url) : null}
              {data.office && row.office_type ? (
                <>
                  {row.template
                    ? modal(
                        'Utwórz kopię szablonu',
                        'plus',
                        `${data.template_create_url}?template=${row.id}`,
                      )
                    : null}
                  {button(
                    row.template ? 'Usuń oznaczenie szablonu' : 'Używaj jako szablonu',
                    'files',
                    row.template_url,
                  )}
                </>
              ) : null}
              {data.office && row.kind === 'text' ? (
                <a className="tasks-project-menu-button" href={row.edit_url}>
                  <Icon name="pencil" />
                  <span>Edytuj dokument</span>
                </a>
              ) : (
                modal(folder ? 'Edytuj folder' : 'Edytuj dane', 'pencil', row.edit_url)
              )}
              {button(
                row.starred ? 'Usuń gwiazdkę' : data.office ? 'Dodaj gwiazdkę' : 'Oznacz gwiazdką',
                'star',
                row.star_url,
              )}
              <a className="tasks-project-menu-button" href={row.download_url} download>
                <Icon name="download" />
                <span>
                  {folder ? 'Pobierz folder ZIP' : row.kind === 'text' ? 'Pobierz DOCX' : 'Pobierz'}
                </span>
              </a>
              {button(
                folder ? 'Usuń pusty folder' : 'Przenieś do kosza',
                'trash-2',
                folder ? row.delete_url : row.trash_url,
                folder ? {} : data.return_values,
                data.office,
              )}
            </>
          )}
        </div>
      )}
    </Dropdown>
  );
}
