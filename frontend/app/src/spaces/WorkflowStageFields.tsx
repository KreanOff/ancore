import { useMemo, useRef, useState } from 'react';
import { FieldControl, type Field, type FormSchema } from '../forms/FormDialog';
import type { ConfigurationData } from './ConfigurationPage';
import { configurationFieldName, configurationStatusKey } from './configuration-form';
import ConfigurationIcon from './ConfigurationIcon';
import ConfigurationColor from './ConfigurationColor';

const scalar = (value: Field['value'] | undefined) =>
  Array.isArray(value) ? value[0] || '' : value || '';

export default function WorkflowStageFields({
  schema,
  data,
  adding,
}: {
  schema: FormSchema;
  data: ConfigurationData;
  adding: boolean;
}) {
  const fields = new Map(schema.fields.map((field) => [configurationFieldName(field), field]));
  const label = fields.get('label');
  const key = fields.get('key');
  const manuallyEditedKey = useRef(false);
  const [generatedKey, setGeneratedKey] = useState(() => scalar(key?.value));
  const keyField = useMemo(() => key && { ...key, value: generatedKey }, [key, generatedKey]);
  const icon = fields.get('icon');
  return (
    <>
      {icon ? (
        <ConfigurationIcon
          field={icon}
          defaultIcon={icon.choices?.find((choice) => choice.value === '')?.icon || 'clock'}
          subject="etapu"
        />
      ) : null}
      <div
        className="space-settings-fields work-flow-stage-form"
        onInput={(event) => {
          if (!(event.target instanceof HTMLInputElement)) return;
          if (event.target.name === key?.name) manuallyEditedKey.current = true;
          if (adding && !manuallyEditedKey.current && event.target.name === label?.name)
            setGeneratedKey(configurationStatusKey(data, event.target.value));
        }}
      >
        <div className="app-form-layout">
          {label ? (
            <div className="app-form-heading">
              <FieldControl field={label} />
            </div>
          ) : null}
          {fields.get('policy') ? (
            <div className="app-form-description">
              <FieldControl field={fields.get('policy')!} />
            </div>
          ) : null}
          {keyField ? <FieldControl field={keyField} /> : null}
          {fields.get('wip_limit') ? <FieldControl field={fields.get('wip_limit')!} /> : null}
          {fields.get('color') ? <ConfigurationColor field={fields.get('color')!} /> : null}
          {schema.fields
            .filter(
              (field) =>
                !['key', 'label', 'icon', 'color', 'wip_limit', 'policy'].includes(
                  configurationFieldName(field),
                ),
            )
            .map((field) =>
              configurationFieldName(field) === 'transitions' ? (
                <div key={field.name} className="app-form-wide work-flow-stage-hint">
                  {(Array.isArray(field.value) ? field.value : []).map((value) => (
                    <input type="hidden" name={field.name} value={value} key={value} />
                  ))}
                  <p>Przejścia między etapami ustawisz w zakładce „Mapa”.</p>
                  {field.errors.map((message) => (
                    <p className="tasks-modal__errors" role="alert" key={message}>
                      {message}
                    </p>
                  ))}
                </div>
              ) : ['category', 'flow_stage'].includes(configurationFieldName(field)) ? (
                <div key={field.name} hidden={!field.errors.length}>
                  <input type="hidden" name={field.name} value={scalar(field.value)} />
                  {field.errors.map((message) => (
                    <p className="tasks-modal__errors" role="alert" key={message}>
                      {message}
                    </p>
                  ))}
                </div>
              ) : (
                <FieldControl field={field} key={field.name} />
              ),
            )}
        </div>
      </div>
    </>
  );
}
