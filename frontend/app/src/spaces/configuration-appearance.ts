import type { Field } from '../forms/FormDialog';

export const configurationBadgeClass =
  'tasks-project-value-badge tasks-project-value-badge--with-icon tasks-project-value-badge--tag-visual';

export function configurationColor(field?: Field) {
  const value = String(field?.value || '').trim();
  return /^#?[0-9a-f]{6}$/i.test(value)
    ? '#' + value.replace('#', '').toLowerCase()
    : field?.attrs?.placeholder || '#64748b';
}
