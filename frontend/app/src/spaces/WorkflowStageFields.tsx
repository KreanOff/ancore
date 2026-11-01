import { useMemo, useState } from 'react';
import { FieldControl, type FormSchema } from '../forms/FormDialog';
import type { ConfigurationData } from './ConfigurationPage';
import { configurationFieldName, configurationStatusKey } from './configuration-form';

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
  const nameField = useMemo(() => label && { ...label, label: 'Nazwa etapu' }, [label]);
  const [generatedKey, setGeneratedKey] = useState(() =>
    String(key?.value || configurationStatusKey(data, String(label?.value || ''))),
  );
  return (
    <div
      className="app-form-layout work-flow-stage-form"
      onInput={(event) => {
        if (adding && event.target instanceof HTMLInputElement && event.target.name === label?.name)
          setGeneratedKey(configurationStatusKey(data, event.target.value));
      }}
    >
      {key?.errors.length ? (
        <FieldControl field={key} />
      ) : key ? (
        <input type="hidden" name={key.name} value={generatedKey} />
      ) : null}
      {['label', 'flow_stage', 'category', 'wip_limit', 'policy'].map((name) => {
        const field = fields.get(name);
        return field ? (
          <FieldControl key={field.name} field={name === 'label' ? nameField! : field} />
        ) : null;
      })}
      {schema.fields
        .filter(
          (field) =>
            !['key', 'label', 'flow_stage', 'category', 'wip_limit', 'policy'].includes(
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
          ) : (
            <FieldControl field={field} key={field.name} />
          ),
        )}
    </div>
  );
}
