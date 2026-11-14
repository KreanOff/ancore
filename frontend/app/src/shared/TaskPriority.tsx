import { Icon } from './Icon';

export function TaskPriority({ value, label = value }: { value: string; label?: string }) {
  const icons: Record<string, string> = {
    urgent: 'circle-alert',
    high: 'arrow-up',
    medium: 'equal',
    low: 'arrow-down',
  };
  return (
    <span
      className={`tasks-row-priority priority-${value}`}
      title={`Priorytet: ${label}`}
      aria-label={`Priorytet: ${label}`}
    >
      <span className="tasks-priority-icon">
        <Icon name={icons[value] || 'circle'} />
      </span>
    </span>
  );
}
