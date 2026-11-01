import { useLayoutEffect, useRef, useState } from 'react';
import type { Field } from '../forms/FormDialog';
import { Icon } from '../shared/Icon';
import type { ConfigurationGroup } from './ConfigurationPage';
import { configurationFieldName as fieldName } from './configuration-form';

const columnIcons: Record<string, string> = {
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
  actions,
}: {
  group: ConfigurationGroup;
  pending: boolean;
  onAdd: () => void;
  onEdit: (index: number) => void;
  onRemove: (indices: number[]) => void;
  actions: {
    dirty: boolean;
    saveDisabled?: boolean;
    cancelDisabled?: boolean;
    onSave: () => void;
    onCancel: () => void;
  };
}) {
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const all = useRef<HTMLInputElement>(null);
  const rows = group.forms.flatMap((schema, index) => {
    const fields = Object.fromEntries(schema.fields.map((field) => [fieldName(field), field]));
    const key = String(fields.key?.value || '');
    return key && !fields.DELETE?.checked ? [{ index, fields, key }] : [];
  });
  const columns =
    group.forms[0]?.fields.filter(
      (field) =>
        !field.hidden &&
        fieldName(field) !== 'DELETE' &&
        !(group.key === 'types' && fieldName(field) === 'icon'),
    ) || [];
  if (group.key === 'types') {
    const order = ['key', 'label', 'description'];
    columns.sort((left, right) => order.indexOf(fieldName(left)) - order.indexOf(fieldName(right)));
  }
  const copy = labels[group.key];
  const maxForms = group.management.fields.find((field) => field.name.endsWith('-MAX_NUM_FORMS'));
  const canAdd = rows.length < Number(maxForms?.value || 30);
  const selectedRows = rows.filter((row) => selected.has(row.index));
  const selectedCount = selectedRows.length;
  useLayoutEffect(() => {
    if (all.current) all.current.indeterminate = selectedCount > 0 && selectedCount < rows.length;
  }, [selectedCount, rows.length]);

  return (
    <>
      <div className="tasks-filterbar tasks-filterbar--directory workplace-edit-modal__team-toolbar member-access-toolbar">
        <button
          type="button"
          className="tasks-filter-button"
          disabled={pending || selectedCount !== 1}
          onClick={() => {
            if (!pending && selectedRows.length === 1) onEdit(selectedRows[0].index);
          }}
          aria-haspopup="dialog"
        >
          <Icon name="pencil" />
          Edytuj
        </button>
        <button
          type="button"
          className="tasks-filter-button"
          disabled={pending || !selectedCount}
          onClick={() => {
            if (pending || !selectedRows.length) return;
            onRemove(selectedRows.map((row) => row.index));
            setSelected(new Set());
          }}
        >
          <Icon name="trash-2" />
          Usuń
        </button>
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
        <div className="member-access-save-actions">
          <button
            type="button"
            className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
            disabled={pending || !actions.dirty || actions.saveDisabled}
            onClick={actions.onSave}
          >
            <Icon name="check" />
            {pending ? 'Zapisywanie…' : 'Zapisz'}
          </button>
          <button
            type="button"
            className="tasks-filter-button"
            disabled={pending || (actions.cancelDisabled ?? (!actions.dirty && !selectedCount))}
            onClick={() => {
              if (pending) return;
              setSelected(new Set());
              actions.onCancel();
            }}
          >
            Anuluj
          </button>
        </div>
      </div>
      {rows.length ? (
        <div
          className={`tasks-table-wrap tasks-board tasks-directory-board tasks-directory-sheet tasks-project-sheet tasks-project-sheet--selectable work-configuration-sheet work-configuration-sheet--${group.key} work-configuration-sheet--toolbar`}
          role="region"
          aria-label={`${group.title} — tabela`}
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.target !== event.currentTarget || pending) return;
            if ((event.ctrlKey || event.metaKey) && event.key === 'a') {
              event.preventDefault();
              setSelected(new Set(rows.map((row) => row.index)));
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
                      event.target.checked ? new Set(rows.map((row) => row.index)) : new Set(),
                    )
                  }
                />
              </span>
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
              {rows.map(({ index, fields }) => {
                const name = displayValue(fields.label);
                const iconValue = fields.icon?.value;
                const selectedIcon = Array.isArray(iconValue) ? iconValue[0] : iconValue;
                const iconChoice = fields.icon?.choices?.find(
                  (option) => option.value === (selectedIcon || ''),
                );
                return (
                  <div
                    className={`tasks-issue-row tasks-directory-row tasks-directory-sheet__row tasks-project-sheet__row ${selected.has(index) ? 'checked' : ''}`}
                    role="row"
                    key={index}
                  >
                    <span
                      className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                      data-column="select"
                      role="cell"
                    >
                      <input
                        type="checkbox"
                        className="tasks-row-checkbox"
                        aria-label={`Zaznacz: ${name}`}
                        disabled={pending}
                        checked={selected.has(index)}
                        onChange={(event) =>
                          setSelected((current) => {
                            const next = new Set(current);
                            if (event.target.checked) next.add(index);
                            else next.delete(index);
                            return next;
                          })
                        }
                      />
                    </span>
                    {columns.map((column) => {
                      const columnKey = fieldName(column);
                      const text = displayValue(fields[columnKey]);
                      return (
                        <div
                          key={columnKey}
                          className={`tasks-directory-sheet__cell tasks-project-sheet__cell${columnKey === 'label' ? ' tasks-directory-name' : ''}`}
                          data-column={columnKey}
                          role="cell"
                          title={text}
                        >
                          {group.key === 'types' && columnKey === 'label' && (
                            <span
                              className="tasks-issue-type"
                              aria-label={`Ikona: ${iconChoice?.label || 'Domyślna dla typu'}`}
                              title={iconChoice?.label || 'Domyślna dla typu'}
                            >
                              <Icon name={iconChoice?.icon || 'shapes'} />
                            </span>
                          )}
                          {columnKey === 'label' ? (
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
