import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
const icons: Record<string, string> = {
  active: 'circle-check',
  inactive: 'circle-x',
  out_of_office: 'circle-arrow-down',
  busy: 'circle-zap',
  do_not_disturb: 'circle-alert',
};
export function PresenceIcon({ value }: { value: string }) {
  return <Icon name={icons[value] || 'circle'} className="profile-presence-icon" />;
}
export default function PresenceSelect({
  value,
  choices,
  onChange,
  side = false,
  disabled = false,
}: {
  value: string;
  choices: { value: string; label: string }[];
  onChange: (value: string) => void;
  side?: boolean;
  disabled?: boolean;
}) {
  return (
    <Dropdown
      label="Status użytkownika"
      searchable={false}
      disabled={disabled}
      className={'profile-status-dropdown' + (side ? ' profile-status-dropdown--side' : '')}
      triggerClassName={'profile-status-button' + (side ? ' profile-status-button--side' : '')}
      menuClass="profile-status-menu"
      trigger={
        <>
          <span className={'profile-status-button-icon presence-' + value}>
            <PresenceIcon value={value} />
          </span>
          <span data-profile-status-selected-label>
            {choices.find((choice) => choice.value === value)?.label}
          </span>
          <Icon name="chevron-down" className="profile-status-caret" />
        </>
      }
    >
      {(close) =>
        choices.map((choice) => (
          <button
            type="button"
            key={choice.value}
            className={'profile-status-option' + (choice.value === value ? ' is-selected' : '')}
            role="menuitemradio"
            aria-checked={choice.value === value}
            onClick={() => {
              close();
              onChange(choice.value);
            }}
          >
            <span className="profile-status-option-check" aria-hidden="true" />
            <span className={'profile-status-option-icon presence-' + choice.value}>
              <PresenceIcon value={choice.value} />
            </span>
            <span>{choice.label}</span>
          </button>
        ))
      }
    </Dropdown>
  );
}
