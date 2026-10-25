import { useEffect, useRef, useState, type RefObject } from 'react';
import { type Page, type PageProps, pageRequest, PageError } from '../shared/page';
import { errorMessage } from '../shared/api';
import type { TaskData } from './types';
import type { FormSchema } from '../forms/FormDialog';
export function useTaskSave(
  form: RefObject<HTMLFormElement>,
  props: PageProps,
  refresh: (data: TaskData) => void,
  validate: (schema: FormSchema) => void,
) {
  const initial = props.initial.data as TaskData;
  const [pending, setPending] = useState(false),
    [dirty, setDirty] = useState(false),
    [error, setError] = useState(initial.error),
    [errors, setErrors] = useState<Record<string, string[]>>(() =>
      Object.fromEntries(
        initial.form.fields
          .filter((field) => field.errors.length)
          .map((field) => [field.name, field.errors]),
      ),
    ),
    [notice, setNotice] = useState('');
  const fieldNames = useRef(
      new Set([...initial.form.fields.map((field) => field.name), 'status', 'files']),
    ),
    changed = useRef(new Map<string, number>()),
    version = useRef(0),
    timer = useRef<ReturnType<typeof setTimeout>>(),
    request = useRef<Promise<boolean> | null>(null),
    needsRefresh = useRef(false),
    life = useRef(new AbortController());
  const saveRef = useRef<() => Promise<boolean>>(async () => true),
    refreshRef = useRef(refresh);
  refreshRef.current = refresh;
  saveRef.current = async () => {
    clearTimeout(timer.current);
    if (request.current) {
      const result = await request.current;
      if (!result) return false;
      if (changed.current.size) return saveRef.current();
      return true;
    }
    if (!changed.current.size && !needsRefresh.current) return true;
    const snapshot = new Map(changed.current);
    setPending(true);
    setError('');
    setNotice(snapshot.size ? 'Zapisywanie…' : 'Odświeżanie…');
    request.current = (async () => {
      let committed = false;
      try {
        if (snapshot.size) {
          const all = new FormData(form.current!),
            body = new FormData();
          snapshot.forEach((_, name) =>
            all.getAll(name).forEach((value) => body.append(name, value)),
          );
          body.set('action', 'save');
          body.set('autosave_fields', JSON.stringify([...snapshot.keys()]));
          await pageRequest(
            props.initial.api_url,
            props.initial.url,
            props.csrfToken,
            life.current.signal,
            body,
          );
          committed = true;
          needsRefresh.current = true;
          snapshot.forEach((value, name) => {
            if (changed.current.get(name) === value) changed.current.delete(name);
          });
          setErrors({});
          setDirty(!!changed.current.size);
          if (!changed.current.size) {
            const input = form.current?.querySelector<HTMLInputElement>('input[name="files"]');
            if (input) input.value = '';
          }
        }
        const page = await pageRequest<Page>(
          props.initial.api_url,
          props.initial.url,
          props.csrfToken,
          life.current.signal,
        );
        refreshRef.current(page.data as TaskData);
        needsRefresh.current = false;
        setErrors({});
        setNotice('Zapisano zmiany.');
        setDirty(!!changed.current.size);
        return true;
      } catch (exception) {
        if (life.current.signal.aborted) return false;
        if (needsRefresh.current && (!snapshot.size || committed)) {
          setError(
            `Zapisano zmiany, ale nie udało się odświeżyć zadania. ${errorMessage(exception)}`,
          );
          setNotice('Zapisano zmiany. Nie udało się odświeżyć zadania.');
          return false;
        }
        if (exception instanceof PageError) {
          const data = exception.data.data as TaskData | undefined;
          if (data?.form) {
            data.form.fields.forEach((field) => fieldNames.current.add(field.name));
            validate(data.form);
            setErrors(
              Object.fromEntries(
                data.form.fields
                  .filter((field) => field.errors.length)
                  .map((field) => [field.name, field.errors]),
              ),
            );
          }
        }
        setError(errorMessage(exception));
        setNotice('Nie zapisano zmian.');
        return false;
      } finally {
        request.current = null;
        setPending(false);
      }
    })();
    const result = await request.current;
    if (result && changed.current.size) return saveRef.current();
    return result;
  };
  useEffect(() => {
    const element = form.current!,
      textValues = new WeakMap<Element, string>();
    function change(event: Event) {
      const input = event.target;
      if (
        !(
          input instanceof HTMLInputElement ||
          input instanceof HTMLTextAreaElement ||
          input instanceof HTMLSelectElement
        ) ||
        !input.name
      )
        return;
      if (!initial.can_edit || !fieldNames.current.has(input.name)) return;
      if (input instanceof HTMLTextAreaElement || input.type === 'text') {
        // Text inputs emit change again on blur, possibly after autosave committed.
        if (textValues.get(input) === input.value) return;
        textValues.set(input, input.value);
      }
      changed.current.set(input.name, ++version.current);
      setDirty(true);
      setNotice('Oczekiwanie na zapis…');
      setError('');
      clearTimeout(timer.current);
      timer.current = setTimeout(
        () => void saveRef.current(),
        input instanceof HTMLSelectElement || input.type === 'checkbox' || input.type === 'file'
          ? 0
          : 700,
      );
    }
    function beforeNavigate(event: Event) {
      if (!changed.current.size && !request.current) return;
      const navigation = event as CustomEvent<{ waitUntil?: (promise: Promise<boolean>) => void }>;
      if (navigation.detail?.waitUntil) navigation.detail.waitUntil(saveRef.current());
      else event.preventDefault();
    }
    function beforeUnload(event: BeforeUnloadEvent) {
      if (changed.current.size || request.current) {
        event.preventDefault();
        event.returnValue = '';
      }
    }
    element.addEventListener('input', change);
    element.addEventListener('change', change);
    document.addEventListener('ancore:before-navigate', beforeNavigate);
    window.addEventListener('beforeunload', beforeUnload);
    return () => {
      clearTimeout(timer.current);
      life.current.abort();
      element.removeEventListener('input', change);
      element.removeEventListener('change', change);
      document.removeEventListener('ancore:before-navigate', beforeNavigate);
      window.removeEventListener('beforeunload', beforeUnload);
    };
  }, []);
  return { pending, dirty, error, errors, notice, save: () => saveRef.current() };
}
