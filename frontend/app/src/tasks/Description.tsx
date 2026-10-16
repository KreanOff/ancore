import { useLayoutEffect, useRef } from 'react';
import type { Field } from '../forms/FormDialog';
// The same allowlist used by enhanceDescriptionEditor in the legacy task screen.
function sanitize(value: string) {
  const template = document.createElement('template');
  template.innerHTML = value;
  const allowed = new Set(['BR', 'DIV', 'P', 'STRONG', 'B', 'EM', 'I', 'UL', 'OL', 'LI']);
  template.content.querySelectorAll('*').forEach((element) => {
    if (!allowed.has(element.tagName)) {
      element.replaceWith(document.createTextNode(element.textContent || ''));
      return;
    }
    [...element.attributes].forEach((attribute) => element.removeAttribute(attribute.name));
  });
  return template.innerHTML;
}
function toHtml(value: string) {
  if (/<\/?[a-z][\s\S]*>/i.test(value)) return sanitize(value);
  return value
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)
    .map((paragraph) => {
      const text = document.createElement('div');
      text.textContent = paragraph;
      return `<p>${text.innerHTML.replace(/\n/g, '<br>')}</p>`;
    })
    .join('');
}
export function Description({ field }: { field: Field }) {
  const source = useRef<HTMLTextAreaElement>(null),
    host = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const element = host.current!,
      input = source.current!;
    element.innerHTML = toHtml(String(field.value || ''));
    input.value = element.innerHTML.trim();
    function sync() {
      input.value = sanitize(element.innerHTML.trim());
      input.dispatchEvent(new Event('input', { bubbles: true }));
    }
    function paste(event: ClipboardEvent) {
      event.preventDefault();
      const html = event.clipboardData?.getData('text/html'),
        text = event.clipboardData?.getData('text/plain') || '';
      const selection = getSelection();
      if (!selection?.rangeCount) return;
      const range = selection.getRangeAt(0);
      if (!element.contains(range.commonAncestorContainer)) return;
      const fragment = range.createContextualFragment(html ? sanitize(html) : toHtml(text)),
        last = fragment.lastChild;
      range.deleteContents();
      range.insertNode(fragment);
      if (last) {
        range.setStartAfter(last);
        range.collapse(true);
        selection.removeAllRanges();
        selection.addRange(range);
      }
      sync();
    }
    if (!field.disabled) {
      element.addEventListener('input', sync);
      element.addEventListener('paste', paste);
    }
    return () => {
      element.removeEventListener('input', sync);
      element.removeEventListener('paste', paste);
    };
  }, [field]);
  return (
    <>
      <textarea
        ref={source}
        id={field.id}
        name={field.name}
        className="form-input tasks-description-source"
        hidden
        disabled={field.disabled}
        defaultValue={String(field.value || '')}
      />
      <div
        ref={host}
        className="form-input tasks-description-editor"
        contentEditable={!field.disabled}
        suppressContentEditableWarning
        role="textbox"
        aria-label="Opis zadania"
        aria-multiline="true"
        aria-readonly={field.disabled || undefined}
        data-placeholder={field.attrs.placeholder || ''}
      />
    </>
  );
}
