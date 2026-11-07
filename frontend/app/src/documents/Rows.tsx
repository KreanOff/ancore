import { EmptyState } from '../shared/EmptyState';
import type { MouseEvent, ReactNode } from 'react';
import { Icon } from '../shared/Icon';
import { DriveIcon, FileIcon, FolderIcon } from './Icons';
import type { DirectoryData, Row } from './types';
export function RowIcon({ row }: { row: Row }) {
  return row.row_kind === 'library' ? (
    <DriveIcon color={row.color} />
  ) : row.row_kind === 'folder' ? (
    <FolderIcon color={row.color} filled={row.has_files} />
  ) : (
    <FileIcon variant={row.variant} />
  );
}
export default function Rows({
  data,
  selected,
  toggle,
  selectAll,
  allRef,
  open,
  dragged,
  drop,
  footer,
}: {
  data: DirectoryData;
  selected: Set<string>;
  toggle: (id: string) => void;
  selectAll: (value: boolean) => void;
  allRef: React.RefObject<HTMLInputElement>;
  open: (url: string) => void;
  dragged: string | null;
  drop: string | null;
  footer?: ReactNode;
}) {
  const sheet = data.libraries || data.office,
    grid = data.display === 'grid';
  function click(event: MouseEvent, row: Row) {
    if (
      row.row_kind === 'document' &&
      !row.full_editor &&
      (!data.office || row.kind === 'file') &&
      !event.metaKey &&
      !event.ctrlKey &&
      !event.shiftKey &&
      !event.altKey
    ) {
      event.preventDefault();
      open(row.url!);
    }
  }
  function name(row: Row, children: ReactNode) {
    return data.view === 'trash' ? (
      <span>{children}</span>
    ) : (
      <a
        href={row.url}
        className={grid ? 'documents-card-entry' : undefined}
        target={row.full_editor ? '_blank' : undefined}
        rel={row.full_editor ? 'noopener' : undefined}
        title={row.name}
        aria-label={row.name}
        onClick={(event) => click(event, row)}
        draggable={false}
      >
        {children}
      </a>
    );
  }
  function location(row: Row) {
    return !data.office && (row.folder_name || !data.library) ? (
      <small>
        {row.folder_name}
        {!data.library ? (
          <>
            {row.folder_name ? ' · ' : ''}
            <a href={row.library_url}>{row.library_name}</a>
          </>
        ) : null}
      </small>
    ) : null;
  }
  function attrs(row: Row) {
    return {
      'data-doc-row': row.id,
      'data-doc-target': row.target,
      'data-doc-label': row.name,
      draggable: !!row.move_url && !data.office && data.view !== 'trash',
      className: `${dragged === row.id ? 'is-document-dragging' : ''} ${drop === row.target ? 'is-document-drop-target' : ''}`,
    };
  }
  const empty = (
    <EmptyState
      illustration="spaces"
      title={
        data.query || data.active_filters
          ? data.libraries
            ? 'Nie znaleziono dysków'
            : data.office
              ? 'Brak pasujących dokumentów'
              : 'Brak wyników'
          : data.libraries
            ? 'Utwórz pierwszy dysk'
            : data.view === 'trash'
              ? 'Kosz jest pusty'
              : data.view === 'starred'
                ? data.office
                  ? 'Brak oznaczonych dokumentów'
                  : 'Brak oznaczonych plików i folderów'
                : data.view === 'templates'
                  ? 'Brak szablonów'
                  : data.office
                    ? 'Twoje dokumenty w jednym miejscu'
                    : data.folder
                      ? 'Ten folder jest pusty'
                      : data.library
                        ? 'Ten dysk jest pusty'
                        : 'Brak plików'
      }
      description={
        data.query || data.active_filters
          ? 'Zmień wyszukiwanie lub wybrane filtry.'
          : data.libraries
            ? 'Dysk to osobne miejsce na foldery i pliki, np. dla projektu lub działu.'
            : data.view === 'trash'
              ? 'Tutaj znajdziesz usunięte pliki.'
              : data.view === 'starred'
                ? 'Oznacz plik lub folder gwiazdką, aby mieć go pod ręką.'
                : data.view === 'templates'
                  ? 'W tym widoku znajdziesz zapisane szablony dokumentów.'
                  : data.office
                    ? 'Twórz dokumenty, arkusze, prezentacje i tablice lub prześlij swoje pliki z komputera.'
                    : 'Prześlij pliki lub utwórz folder, aby uporządkować pracę.'
      }
    />
  );
  if (!data.rows.length) return <div className="documents-table-scroll">{empty}</div>;
  if (grid)
    return (
      <div className="documents-grid-scroll">
        <ul
          className={`documents-grid ${data.libraries ? 'documents-grid--libraries' : ''}`}
          aria-label={
            data.libraries
              ? 'Dyski — kafelki'
              : data.office
                ? 'Dokumenty — kafelki'
                : 'Pliki i foldery — kafelki'
          }
        >
          {data.rows.map((row) => (
            <li
              key={row.id}
              {...attrs(row)}
              className={`documents-card ${data.libraries ? 'documents-card--library' : row.row_kind === 'folder' ? 'documents-card--folder' : ''} ${attrs(row).className}`}
            >
              {name(
                row,
                <>
                  <span className="documents-card-preview" aria-hidden="true">
                    {data.libraries ? (
                      <span className="documents-library-icon">
                        <RowIcon row={row} />
                      </span>
                    ) : (
                      <RowIcon row={row} />
                    )}{' '}
                    {!data.libraries && row.row_kind !== 'folder' ? (
                      <small>{row.extension}</small>
                    ) : null}
                  </span>
                  <span className="documents-card-title">{row.name}</span>
                  {!data.libraries ? (
                    <span className="documents-card-meta">
                      {row.row_kind === 'folder' ? 'Folder' : `${row.extension} · ${row.size}`}
                    </span>
                  ) : null}
                </>,
              )}
              {!data.office && !data.libraries && (row.folder_name || !data.library) ? (
                <p className="documents-card-location">
                  {!data.library ? <a href={row.library_url}>{row.library_name}</a> : null}
                  {!data.library && row.folder_name ? ' / ' : ''}
                  {row.folder_name ? <a href={row.folder_url}>{row.folder_name}</a> : null}
                </p>
              ) : null}
              <div className="documents-card-footer">
                <span className="documents-card-date">
                  {!data.office && data.view === 'trash' ? row.deleted : row.date}
                </span>
              </div>
            </li>
          ))}
        </ul>
        {footer}
      </div>
    );
  if (sheet)
    return (
      <div
        className={`documents-table-scroll tasks-table-wrap tasks-board tasks-directory-board tasks-directory-sheet tasks-project-sheet tasks-project-sheet--selectable ${data.libraries ? 'documents-library-sheet' : 'office-document-sheet'} app-data-table`}
      >
        <div
          className="tasks-directory-group"
          role="table"
          aria-label={data.libraries ? 'Lista dysków' : 'Lista dokumentów'}
        >
          <div
            className="tasks-directory-header tasks-directory-sheet__header tasks-project-sheet__header app-table-header"
            role="row"
          >
            <span
              className="tasks-directory-header-select tasks-directory-sheet__cell tasks-project-sheet__cell"
              data-column="select"
              role="columnheader"
              onClick={(e) => {
                if (e.target === e.currentTarget) selectAll(selected.size !== data.rows.length);
              }}
            >
              <input
                ref={allRef}
                type="checkbox"
                className="tasks-row-checkbox"
                aria-label={`Zaznacz wszystkie ${data.libraries ? 'dyski' : 'dokumenty'} w widocznej liście`}
                checked={selected.size === data.rows.length}
                onChange={(e) => selectAll(e.target.checked)}
              />
            </span>
            {[
              ['name', 'Nazwa', data.libraries ? 'hard-drive' : 'file-text'],
              ['modified', 'Zmodyfikowano', 'calendar-clock'],
              ['size', 'Rozmiar', 'hard-drive'],
            ].map(([key, label, icon]) => (
              <span
                key={key}
                className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                data-column={key}
                role="columnheader"
              >
                {label}
                <Icon name={icon} />
              </span>
            ))}
          </div>
          <div className="tasks-issue-list tasks-directory-list" role="presentation">
            {data.rows.map((row) => (
              <div
                key={row.id}
                {...attrs(row)}
                className={`tasks-issue-row tasks-directory-row tasks-directory-sheet__row tasks-project-sheet__row app-table-row ${selected.has(row.id) ? 'checked' : ''} ${attrs(row).className}`}
                role="row"
              >
                <span
                  className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                  data-column="select"
                  role="cell"
                  onClick={(e) => {
                    if (e.target === e.currentTarget) toggle(row.id);
                  }}
                >
                  <input
                    type="checkbox"
                    className="tasks-row-checkbox"
                    aria-label={`Zaznacz ${data.libraries ? 'dysk' : 'dokument'} ${row.name}`}
                    checked={selected.has(row.id)}
                    onChange={() => toggle(row.id)}
                  />
                </span>

                <div
                  className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                  data-column="name"
                  role="cell"
                >
                  {data.libraries ? (
                    <a
                      className="documents-library-entry"
                      href={row.url}
                      title={`Otwórz dysk: ${row.name}`}
                    >
                      <span className="documents-library-icon">
                        <RowIcon row={row} />
                      </span>
                      <span className="documents-library-copy">
                        <span className="documents-library-title">{row.name}</span>
                      </span>
                    </a>
                  ) : (
                    <div className="documents-name">
                      <span className="documents-file-icon">
                        <RowIcon row={row} />
                      </span>
                      <div>{name(row, row.name)}</div>
                    </div>
                  )}
                </div>
                <div
                  className="tasks-project-sheet__date tasks-directory-sheet__cell tasks-project-sheet__cell"
                  data-column="modified"
                  role="cell"
                  title={`Zmodyfikowano: ${row.datetime}`}
                >
                  {row.date}
                </div>
                <div
                  className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                  data-column="size"
                  role="cell"
                >
                  {row.size}
                </div>
              </div>
            ))}
          </div>
        </div>
        {footer}
      </div>
    );
  return (
    <div className="documents-table-scroll">
      <table className="documents-table documents-table--inline-actions app-data-table app-data-table--native">
        <thead>
          <tr>
            <th scope="col">
              <span className="documents-column-heading app-table-heading">
                <Icon name="file-text" />
                Nazwa
              </span>
            </th>
            <th scope="col" data-document-column="date">
              <span className="documents-column-heading app-table-heading">
                <Icon name="calendar-clock" />
                Zmodyfikowano
              </span>
            </th>
            <th scope="col" data-document-column="size">
              <span className="documents-column-heading app-table-heading">
                <Icon name="hard-drive" />
                Rozmiar
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row) => (
            <tr key={row.id} {...attrs(row)}>
              <td>
                <div className="documents-name">
                  <span
                    className={`documents-file-icon ${row.row_kind === 'folder' ? 'documents-file-icon--folder' : ''}`}
                  >
                    <RowIcon row={row} />
                  </span>
                  <div>
                    {name(row, row.name)}
                    {location(row)}
                  </div>
                </div>
              </td>
              <td
                className="documents-date"
                data-document-column="date"
                title={data.view === 'trash' ? `Usunięto: ${row.deleted}` : undefined}
              >
                {row.date}
              </td>
              <td className="documents-size" data-document-column="size">
                {row.size}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {footer}
    </div>
  );
}
