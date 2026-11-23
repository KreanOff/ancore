import { Icon } from './Icon';

export function WorkspaceNameButton({
  inputId,
  className,
  disabled,
  onClick,
}: {
  inputId: string;
  className: string;
  disabled?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      className={className}
      data-workspace-name-generator={onClick ? undefined : ''}
      aria-controls={inputId}
      aria-label="Wylosuj nazwę Workspace"
      title="Wylosuj nazwę Workspace"
      disabled={disabled}
      onClick={onClick}
    >
      <Icon name="sparkles" />
    </button>
  );
}
