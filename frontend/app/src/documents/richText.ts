// Attribute-free format shared with documents/rich_text.py and legacy office.js.
export function safeFragment(html: string) {
  const template = document.createElement('template');
  template.innerHTML = html;
  const allowed = new Set([
    'p',
    'br',
    'h1',
    'h2',
    'h3',
    'strong',
    'em',
    'u',
    's',
    'ul',
    'ol',
    'li',
    'blockquote',
  ]);
  const blocked = new Set(['script', 'style', 'iframe', 'object', 'svg', 'math', 'template']);
  const aliases: Record<string, string> = { div: 'p', b: 'strong', i: 'em', strike: 's' };
  function copy(from: Node, to: Node, depth = 0) {
    if (depth > 64) return;
    for (const child of from.childNodes) {
      if (child.nodeType === Node.TEXT_NODE)
        to.appendChild(document.createTextNode(child.textContent || ''));
      else if (child instanceof Element && !blocked.has(child.localName)) {
        const tag = aliases[child.localName] || child.localName;
        if (allowed.has(tag)) {
          const clean = document.createElement(tag);
          copy(child, clean, depth + 1);
          to.appendChild(clean);
        } else copy(child, to, depth + 1);
      }
    }
  }
  const result = document.createDocumentFragment();
  copy(template.content, result);
  return result;
}
