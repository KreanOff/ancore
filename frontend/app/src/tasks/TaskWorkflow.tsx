import type { Item } from '../spaces/types';

export function TaskWorkflowStatus({ item }: { item: Item }) {
  return (
    <div className="tasks-issue-field task-workflow-field">
      <span className="tasks-issue-field-label" id="task-workflow-label">
        Etap zadania
      </span>
      <div className="task-workflow__current" aria-label={`Bieżący etap: ${item.status_label}`}>
        <span className={`status-indicator status-${item.category}`} aria-hidden="true" />
        <span>{item.status_label}</span>
      </div>
    </div>
  );
}

export function TaskWorkflowActions({
  item,
  canEdit,
  disabled,
  pending,
  requestedStatus,
  onTransition,
  errors = [],
}: {
  item: Item;
  canEdit: boolean;
  disabled: boolean;
  pending: boolean;
  requestedStatus: string;
  onTransition: (status: string) => void;
  errors?: string[];
}) {
  const transitions = item.transitions ?? [];
  const requested = transitions.find((status) => status.key === requestedStatus);
  if (!canEdit) return null;
  return (
    <section
      className="tasks-issue-side-section task-workflow-actions"
      aria-label="Zmiana etapu zadania"
      aria-busy={pending}
    >
      {transitions.length ? (
        <div className="task-workflow__transitions" role="group" aria-label="Dostępne przejścia">
          {transitions.map((status) => (
            <button
              key={status.key}
              type="button"
              className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight task-workflow__transition"
              disabled={disabled}
              aria-label={`Przejdź do: ${status.label}`}
              title={status.policy || `Przejdź do: ${status.label}`}
              onClick={() => onTransition(status.key)}
            >
              <span className={`status-indicator status-${status.category}`} aria-hidden="true" />
              <span>{status.label}</span>
            </button>
          ))}
        </div>
      ) : (
        <p className="task-workflow__hint">Brak dalszych przejść.</p>
      )}
      {requested ? (
        <p className="task-workflow__hint" role="status">
          {pending ? 'Zapisywanie przejścia' : 'Wybrane przejście'}: {requested.label}
        </p>
      ) : null}
      {errors.map((message) => (
        <p role="alert" className="tasks-modal__errors" key={message}>
          {message}
        </p>
      ))}
    </section>
  );
}
