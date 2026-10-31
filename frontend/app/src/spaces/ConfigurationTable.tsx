import { useLayoutEffect, useRef, useState } from 'react';
import type { Field } from '../forms/FormDialog';
import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import type { ConfigurationGroup } from './ConfigurationPage';
import { configurationFieldName as fieldName, configurationHasRow } from './configuration-form';

const columnIcons: Record<string, string> = {
  icon: 'shapes',
  key: 'hash',
  label: 'align-left',
  description: 'file-text',
  category: 'list-checks',
  transitions: 'workflow',
  type: 'list-ordered',
  required: 'check',
};
const labels = {
  types: { add: 'Dodaj typ', empty: 'Brak typów zgłoszeń.' },
  statuses: { add: 'Dodaj status', empty: 'Brak statusów.' },
  fields: { add: 'Dodaj pole', empty: 'Brak pól dodatkowych.' },
};

function displayValue(field: Field) {
  if (field.type === 'checkbox') return field.checked ? 'Tak' : 'Nie';
  const values = Array.isArray(field.value) ? field.value : [field.value];
  return (
    values
      .filter((value) => value !== null && value !== '')
      .map((value) => field.choices?.find((choice) => choice.value === value)?.label || value)
      .join(', ') || '—'
  );
}

export default function ConfigurationTable({
  group,
  pending,
  onAdd,
  onEdit,
  onRemove,
}: {
  group: ConfigurationGroup;
  pending: boolean;
  onAdd: () => void;
  onEdit: (index: number) => void;
  onRemove: (index: number) => void;
}) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const all = useRef<HTMLInputElement>(null);
  const rows = group.forms.flatMap((schema, index) => {
    const fields = Object.fromEntries(schema.fields.map((field) => [fieldName(field), field]));
    const key = String(fields.key?.value || '');
    return key && !fields.DELETE?.checked ? [{ index, fields, key }] : [];
  });
  const columns =
    group.forms[0]?.fields.filter((field) => !field.hidden && fieldName(field) !== 'DELETE') || [];
  if (group.key === 'types') {
    const order = ['icon', 'key', 'label', 'description'];
    columns.sort((left, right) => order.indexOf(fieldName(left)) - order.indexOf(fieldName(right)));
  }
  const copy = labels[group.key];
  const canAdd = group.forms.some((schema) => !configurationHasRow(schema));
  const selectedCount = rows.filter((row) => selected.has(row.key)).length;
  useLayoutEffect(() => {
    if (all.current) all.current.indeterminate = selectedCount > 0 && selectedCount < rows.length;
  }, [selectedCount, rows.length]);

  return (
    <>
      <div className="workplace-edit-modal__team-toolbar">
        <button
          type="button"
          className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
          disabled={pending || !canAdd}
          onClick={onAdd}
          aria-haspopup="dialog"
        >
          <Icon name="plus" />
          {copy.add}
        </button>
      </div>
      {rows.length ? (
        <div
          className={`tasks-table-wrap tasks-board tasks-directory-board tasks-directory-sheet tasks-project-sheet tasks-project-sheet--selectable work-configuration-sheet work-configuration-sheet--${group.key}`}
          role="region"
          aria-label={`${group.title} — tabela`}
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.target !== event.currentTarget || pending) return;
            if ((event.ctrlKey || event.metaKey) && event.key === 'a') {
              event.preventDefault();
              setSelected(new Set(rows.map((row) => row.key)));
            } else if (event.key === 'Escape') setSelected(new Set());
          }}
        >
          <section className="tasks-directory-group" role="table" aria-label={group.title}>
            <div
              className="tasks-directory-header tasks-directory-sheet__header tasks-project-sheet__header"
              role="row"
            >
              <span
                className="tasks-directory-header-select tasks-directory-sheet__cell tasks-project-sheet__cell"
                data-column="select"
                role="columnheader"
              >
                <input
                  ref={all}
                  type="checkbox"
                  className="tasks-row-checkbox"
                  aria-label="Zaznacz wszystkie pozycje"
                  disabled={pending}
                  checked={selectedCount === rows.length}
                  onChange={(event) =>
                    setSelected(
                      event.target.checked ? new Set(rows.map((row) => row.key)) : new Set(),
                    )
                  }
                />
              </span>
              <span
                className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                data-column="action"
                role="columnheader"
                aria-label="Działania"
              />
              {columns.map((field) => (
                <span
                  key={field.name}
                  className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                  data-column={fieldName(field)}
                  role="columnheader"
                >
                  <Icon name={columnIcons[fieldName(field)] || 'list-ordered'} />
                  {group.key === 'fields' && fieldName(field) === 'key'
                    ? 'Klucz pola'
                    : group.key === 'fields' && fieldName(field) === 'label'
                      ? 'Nazwa pola'
                      : field.label}
                </span>
              ))}
            </div>
            <div className="tasks-issue-list tasks-directory-list" role="rowgroup">
              {rows.map(({ index, fields, key }) => {
                const name = displayValue(fields.label);
                return (
                  <div
                    className={`tasks-issue-row tasks-directory-row tasks-directory-sheet__row tasks-project-sheet__row ${selected.has(key) ? 'checked' : ''}`}
                    role="row"
                    key={key}
                  >
                    <input
                      type="checkbox"
                      className="tasks-row-checkbox tasks-directory-sheet__cell tasks-project-sheet__cell"
                      data-column="select"
                      aria-label={`Zaznacz: ${name}`}
                      disabled={pending}
                      checked={selected.has(key)}
                      onChange={(event) =>
                        setSelected((current) => {
                          const next = new Set(current);
                          if (event.target.checked) next.add(key);
                          else next.delete(key);
                          return next;
                        })
                      }
                    />
                    <div
                      className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                      data-column="action"
                      role="cell"
                    >
                      <Dropdown
                        searchable={false}
                        label={`Działania: ${name}`}
                        menuClass="documents-item-menu"
                        disabled={pending}
                        trigger={<Icon name="menu" />}
                      >
                        {(close) => (
                          <div className="documents-menu-actions">
                            <button
                              type="button"
                              role="menuitem"
                              className="tasks-project-menu-button"
                              disabled={pending}
                              onClick={() => {
                                close();
                                onEdit(index);
                              }}
                            >
                              <Icon name="pencil" />
                              <span>Edytuj</span>
                            </button>
                            <button
                              type="button"
                              role="menuitem"
                              className="tasks-project-menu-button"
                              disabled={pending}
                              onClick={() => {
                                close();
                                onRemove(index);
                              }}
                            >
                              <Icon name="trash-2" />
                              <span>Usuń</span>
                            </button>
                          </div>
                        )}
                      </Dropdown>
                    </div>
                    {columns.map((column) => {
                      const columnKey = fieldName(column);
                      const value = fields[columnKey].value;
                      const selectedValue = Array.isArray(value) ? value[0] : value;
                      const choice = fields[columnKey].choices?.find(
                        (option) => option.value === (selectedValue || ''),
                      );
                      const text =
                        columnKey === 'icon'
                          ? choice?.label || 'Domyślna dla typu'
                          : displayValue(fields[columnKey]);
                      return (
                        <div
                          key={columnKey}
                          className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                          data-column={columnKey}
                          role="cell"
                          title={text}
                        >
                          {columnKey === 'icon' ? (
                            <span className="tasks-issue-type" aria-label={`Ikona: ${text}`}>
                              <Icon name={choice?.icon || 'shapes'} />
                            </span>
                          ) : columnKey === 'label' ? (
                            <button
                              type="button"
                              className="work-configuration-name"
                              disabled={pending}
                              aria-label={`Edytuj: ${name}`}
                              aria-haspopup="dialog"
                              onClick={() => onEdit(index)}
                            >
                              {text}
                            </button>
                          ) : (
                            <span className="workplace-team__name">{text}</span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          </section>
        </div>
      ) : (
        <p className="work-empty">{copy.empty}</p>
      )}
    </>
  );
}
