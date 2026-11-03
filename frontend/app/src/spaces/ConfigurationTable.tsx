import { useState, type CSSProperties } from 'react';
import { LocalDirectoryTable } from '../shared/LocalDirectoryTable';
import type { Field } from '../forms/FormDialog';
import { Icon } from '../shared/Icon';
import type { ConfigurationGroup } from './ConfigurationPage';
import { configurationFieldName as fieldName } from './configuration-form';
import { configurationBadgeClass, configurationColor } from './configuration-appearance';

const columnIcons: Record<string, string> = {
  key: 'hash',
  label: 'align-left',
  description: 'file-text',
  category: 'list-checks',
  transitions: 'workflow',
  flow_stage: 'workflow',
  wip_limit: 'gauge',
  policy: 'file-text',
  type: 'list-ordered',
  required: 'check',
};
const labels = {
  types: { add: 'Dodaj typ', empty: 'Brak typów zgłoszeń.' },
  statuses: { add: 'Dodaj stan', empty: 'Brak stanów.' },
  fields: { add: 'Dodaj pole', empty: 'Brak pól dodatkowych.' },
  categories: { add: 'Dodaj kategorię', empty: 'Brak kategorii.' },
  groups: { add: 'Dodaj grupę', empty: 'Brak grup.' },
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
  onMove,
  actions,
}: {
  group: ConfigurationGroup;
  pending: boolean;
  onAdd: () => void;
  onEdit: (index: number) => void;
  onRemove: (indices: number[]) => void;
  onMove?: (index: number, direction: -1 | 1) => void;
  actions?: {
    dirty: boolean;
    saveDisabled?: boolean;
    cancelDisabled?: boolean;
    onSave: () => void;
    onCancel: () => void;
  };
}) {
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const rows = group.forms.flatMap((schema, index) => {
    const fields = Object.fromEntries(schema.fields.map((field) => [fieldName(field), field]));
    const key = String(fields.key?.value || '');
    return key && !fields.DELETE?.checked ? [{ index, fields, key }] : [];
  });
  const columns =
    group.forms[0]?.fields.filter(
      (field) => !field.hidden && !['DELETE', 'icon', 'color'].includes(fieldName(field)),
    ) || [];
  if (['types', 'categories', 'groups'].includes(group.key)) {
    const order = ['key', 'label', 'description'];
    columns.sort((left, right) => order.indexOf(fieldName(left)) - order.indexOf(fieldName(right)));
  }
  const copy = labels[group.key];
  const maxForms = group.management.fields.find((field) => field.name.endsWith('-MAX_NUM_FORMS'));
  const canAdd = rows.length < Number(maxForms?.value || 30);
  const selectedRows = rows.filter((row) => selected.has(row.index));
  const selectedCount = selectedRows.length;

  return (
    <>
      <LocalDirectoryTable
        segment={`space-settings-${group.key}`}
        label={group.title}
        searchLabel={
          group.key === 'types'
            ? 'Szukaj typów zgłoszeń'
            : group.key === 'statuses'
              ? 'Szukaj stanów'
              : group.key === 'categories'
                ? 'Szukaj kategorii'
                : group.key === 'groups'
                  ? 'Szukaj grup'
                  : 'Szukaj pól'
        }
        emptyLabel={copy.empty}
        busy={pending}
        selected={selected}
        onSelect={setSelected}
        columns={columns.map((field) => {
          const key = fieldName(field);
          const widths: Record<string, number> = {
            key: 250,
            label: 250,
            description: 320,
            category: 180,
            flow_stage: 180,
            wip_limit: 230,
            policy: 300,
            transitions: 320,
          };
          return {
            key,
            label:
              group.key === 'fields' && key === 'key'
                ? 'Klucz pola'
                : group.key === 'fields' && key === 'label'
                  ? 'Nazwa pola'
                  : field.label,
            icon: columnIcons[key] || 'list-ordered',
            width: widths[key] || 180,
            filterable: ['key', 'category', 'flow_stage', 'type', 'required'].includes(key),
          };
        })}
        rows={rows.map(({ index, fields }) => {
          const name = displayValue(fields.label);
          const iconValue = fields.icon?.value;
          const selectedIcon = Array.isArray(iconValue) ? iconValue[0] : iconValue;
          const iconChoice = fields.icon?.choices?.find(
            (option) => option.value === (selectedIcon || ''),
          );
          return {
            id: index,
            label: name,
            values: Object.fromEntries(
              columns.map((column) => [fieldName(column), displayValue(fields[fieldName(column)])]),
            ),
            cells: {
              label: (
                <>
                  <button
                    type="button"
                    className="work-configuration-name"
                    disabled={pending}
                    aria-label={`Edytuj: ${name}`}
                    aria-haspopup="dialog"
                    onClick={() => onEdit(index)}
                  >
                    {group.key === 'categories' || group.key === 'groups' ? (
                      <span className="work-configuration-badge-label">{name}</span>
                    ) : (
                      <span
                        className={configurationBadgeClass}
                        style={{ '--tag-color': configurationColor(fields.color) } as CSSProperties}
                      >
                        {fields.icon ? <Icon name={iconChoice?.icon || 'shapes'} /> : null}
                        <span className="work-configuration-badge-label">{name}</span>
                      </span>
                    )}
                  </button>
                </>
              ),
            },
          };
        })}
      >
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
          {onMove
            ? ([-1, 1] as const).map((direction) => (
                <button
                  type="button"
                  className="tasks-filter-button"
                  key={direction}
                  disabled={
                    pending ||
                    selectedCount !== 1 ||
                    rows.findIndex((row) => row.index === selectedRows[0]?.index) ===
                      (direction === -1 ? 0 : rows.length - 1)
                  }
                  onClick={() => {
                    if (pending || selectedRows.length !== 1) return;
                    const position = rows.findIndex((row) => row.index === selectedRows[0].index);
                    onMove(selectedRows[0].index, direction);
                    setSelected(new Set([rows[position + direction].index]));
                  }}
                >
                  <Icon name={direction === -1 ? 'arrow-left' : 'arrow-right'} />
                  {direction === -1 ? 'W lewo' : 'W prawo'}
                </button>
              ))
            : null}
          {actions && group.key !== 'statuses' ? (
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
          ) : null}
        </div>
      </LocalDirectoryTable>
    </>
  );
}
