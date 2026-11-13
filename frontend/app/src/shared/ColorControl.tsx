import { type ReactNode, useRef } from 'react';

export function ColorControl({
  id,
  name,
  value,
  color,
  label,
  placeholder,
  pattern,
  disabled,
  invalid,
  describedBy,
  onChange,
  children,
}: {
  id: string;
  name: string;
  value: string;
  color: string;
  label: string;
  placeholder?: string;
  pattern?: string;
  disabled?: boolean;
  invalid?: boolean;
  describedBy?: string;
  onChange: (value: string) => void;
  children: ReactNode;
}) {
  const input = useRef<HTMLInputElement>(null);
  function choose(next: string) {
    onChange(next);
    input.current!.value = next;
    input.current!.dispatchEvent(new Event('input', { bubbles: true }));
  }
  return (
    <div className="documents-color-control work-configuration-color">
      <input
        type="color"
        className="documents-color-input"
        aria-label={label}
        value={color}
        disabled={disabled}
        aria-invalid={invalid}
        aria-describedby={describedBy}
        onChange={(event) => choose(event.target.value)}
      />
      <input
        ref={input}
        id={id}
        name={name}
        className="form-input"
        value={value}
        placeholder={placeholder}
        maxLength={7}
        pattern={pattern}
        disabled={disabled}
        aria-invalid={invalid}
        aria-describedby={describedBy}
        onChange={(event) => onChange(event.target.value)}
      />
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        disabled={disabled}
        onClick={() => choose('')}
      >
        Domyślny
      </button>
      {children}
    </div>
  );
}
