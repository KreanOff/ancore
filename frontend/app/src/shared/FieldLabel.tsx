import { type ReactNode, useId } from 'react';

export function FieldLabel({
  htmlFor,
  label,
  required = false,
  helpText,
  helpId,
  helpLabel,
}: {
  htmlFor?: string;
  label: ReactNode;
  required?: boolean;
  helpText?: string;
  helpId?: string;
  helpLabel?: string;
}) {
  const generatedId = useId();
  const id = helpId || generatedId;
  return (
    <div className="app-field-label">
      <label htmlFor={htmlFor}>
        {label}
        {required ? <span aria-hidden="true"> *</span> : null}
      </label>
      {helpText ? (
        <span className="app-field-help" data-field-help>
          <button
            type="button"
            className="app-field-help__trigger"
            data-field-help-toggle
            aria-label={`Informacja: ${helpLabel || (typeof label === 'string' ? label : 'pole')}`}
            aria-describedby={id}
            aria-controls={id}
            aria-expanded="false"
          >
            <span aria-hidden="true">!</span>
          </button>
          <span
            id={id}
            className="app-field-help__content"
            data-field-help-content
            data-dropdown-search-disabled
            data-dropdown-placement="top"
            role="tooltip"
            hidden
          >
            {helpText}
          </span>
        </span>
      ) : null}
    </div>
  );
}
