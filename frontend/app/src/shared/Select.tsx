import { useId, useLayoutEffect, useRef } from 'react';

// An imperative island keeps the shared custom select outside React's DOM ownership.
export function Select({
  label,
  name,
  value,
  options,
  onChange,
  hideLabel = false,
  required = false,
  disabled = false,
  invalid = false,
  describedBy,
}: {
  label: string;
  name?: string;
  value: string;
  options: [string, string][];
  onChange: (value: string) => void;
  hideLabel?: boolean;
  required?: boolean;
  disabled?: boolean;
  invalid?: boolean;
  describedBy?: string;
}) {
  const host = useRef<HTMLDivElement>(null);
  const handler = useRef(onChange);
  const restoreFocus = useRef(false);
  handler.current = onChange;
  const id = useId();
  useLayoutEffect(() => {
    const element = host.current!;
    const select = document.createElement('select');
    select.id = id;
    if (name) select.name = name;
    select.setAttribute('aria-label', label);
    select.required = required;
    select.disabled = disabled;
    select.setAttribute('aria-invalid', String(invalid));
    if (describedBy) select.setAttribute('aria-describedby', describedBy);
    select.className = hideLabel ? 'tasks-inline-select' : 'form-select';
    options.forEach(([key, text]) => select.add(new Option(text, key)));
    select.value = value;
    element.append(select);
    select.addEventListener('change', () => handler.current(select.value));
    window.AncoreCustomSelect?.refresh(element);
    const trigger = element.querySelector<HTMLButtonElement>('[data-ancore-custom-select-toggle]');
    if (trigger) {
      trigger.setAttribute('aria-invalid', String(invalid));
      if (required) trigger.setAttribute('aria-required', 'true');
      if (describedBy) trigger.setAttribute('aria-describedby', describedBy);
    }
    // The custom select returns focus to its trigger before changing the React value.
    if (restoreFocus.current && !disabled && document.activeElement === document.body) {
      (trigger || select).focus({ preventScroll: true });
    }
    return () => {
      restoreFocus.current = element.contains(document.activeElement);
      element.replaceChildren();
    };
  }, [id, label, name, options, value, hideLabel, required, disabled, invalid, describedBy]);
  return (
    <div
      className={`documents-field resources-react-filter ${hideLabel ? 'react-select-inline' : ''}`}
    >
      <label htmlFor={id} className={hideLabel ? 'u-sr-only' : undefined}>
        {label}
      </label>
      <div ref={host} />
    </div>
  );
}
