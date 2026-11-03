import { useState } from 'react';
import { FieldControl, type Field, type FormSchema } from '../forms/FormDialog';
import { configurationFieldName } from './configuration-form';
import ConfigurationIcon from './ConfigurationIcon';
import ConfigurationColor from './ConfigurationColor';

const scalar = (value: Field['value']) => (Array.isArray(value) ? value[0] || '' : value || '');

export default function TypeFields({
  schema,
  iconDefaults,
  fallbackIcon = 'shapes',
  subject = 'typu',
}: {
  schema: FormSchema;
  iconDefaults?: Record<string, string>;
  fallbackIcon?: string;
  subject?: 'typu' | 'kategorii' | 'grupy';
}) {
  const fields = Object.fromEntries(
    schema.fields.map((field) => [configurationFieldName(field), field]),
  );
  const [key, setKey] = useState(() => scalar(fields.key?.value));
  const defaultIcon =
    iconDefaults?.[key] ||
    (!iconDefaults && key === scalar(fields.key?.value)
      ? fields.icon?.choices?.find((choice) => choice.value === '')?.icon
      : undefined) ||
    fallbackIcon;
  return (
    <>
      {fields.icon ? (
        <ConfigurationIcon field={fields.icon} defaultIcon={defaultIcon} subject={subject} />
      ) : null}
      <div
        className={`space-settings-fields${fields.icon ? '' : ' app-form-wide'}`}
        onInput={(event) => {
          const target = event.target;
          if (target instanceof HTMLInputElement && target.name === fields.key?.name)
            setKey(target.value);
        }}
      >
        <div className="app-form-layout">
          {fields.label ? (
            <div className="app-form-heading">
              <FieldControl field={fields.label} />
            </div>
          ) : null}
          {fields.description ? (
            <div className="app-form-description">
              <FieldControl field={fields.description} />
            </div>
          ) : null}
          {fields.key ? <FieldControl field={fields.key} /> : null}
          {fields.color ? <ConfigurationColor field={fields.color} /> : null}
          {schema.fields
            .filter((field) => field.hidden)
            .map((field) => (
              <FieldControl field={field} key={field.name} />
            ))}
        </div>
      </div>
    </>
  );
}
