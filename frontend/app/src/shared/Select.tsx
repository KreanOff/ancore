import { useId, useLayoutEffect, useRef } from 'react';

// An imperative island keeps the shared custom select outside React's DOM ownership.
export function Select({
  label,
  name,
  value,
  options,
  onChange,
  hideLabel = false,
}: {
  label: string;
  name?: string;
  value: string;
  options: [string, string][];
  onChange: (value: string) => void;
  hideLabel?: boolean;
}) {
  const host = useRef<HTMLDivElement>(null);
  const handler = useRef(onChange);
  handler.current = onChange;
  const id = useId();
  useLayoutEffect(() => {
    const element = host.current!;
    const select = document.createElement('select');
    select.id = id;
    if (name) select.name = name;
    select.setAttribute('aria-label', label);
    select.className = hideLabel ? 'tasks-inline-select' : 'form-select';
    options.forEach(([key, text]) => select.add(new Option(text, key)));
    select.value = value;
    element.append(select);
    select.addEventListener('change', () => handler.current(select.value));
    window.AncoreCustomSelect?.refresh(element);
    return () => {
      element.replaceChildren();
    };
  }, [id, label, name, options, value, hideLabel]);
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
