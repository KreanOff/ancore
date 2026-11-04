import { type ChangeEvent, type FormEvent, useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { Modal } from '../shared/Modal';
import { Icon } from '../shared/Icon';
import { errorMessage } from '../shared/api';
import { PageError, pageRequest, type Page } from '../shared/page';
import type { ProfileData } from './types';
import BannerCropper from './BannerCropper';
import {
  bannerCropFromFields,
  DEFAULT_BANNER_CROP,
  normalizeBannerCrop,
  sameBannerCrop,
  type BannerCrop,
} from './banner-crop';

const imageTypes = new Set(['image/png', 'image/jpeg', 'image/webp']);

export default function BannerEditor({
  data,
  api,
  token,
  onClose,
}: {
  data: ProfileData;
  api: string;
  token: string;
  onClose: () => void;
}) {
  const [schema, setSchema] = useState(data.banner_form);
  const [file, setFile] = useState<File | null>(null);
  const [objectUrl, setObjectUrl] = useState('');
  const [remove, setRemove] = useState(
    Boolean(data.banner_form.fields.find((field) => field.name === 'remove_banner')?.checked),
  );
  const [crop, setCrop] = useState(() =>
    remove
      ? DEFAULT_BANNER_CROP
      : data.banner_form.bound
        ? bannerCropFromFields(data.banner_form.fields, data.banner.crop)
        : normalizeBannerCrop(data.banner.crop),
  );
  const [previewReady, setPreviewReady] = useState(false);
  const [dirty, setDirty] = useState(data.banner_form.bound);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState('');
  const [fileError, setFileError] = useState('');
  const form = useRef<HTMLFormElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const alert = useRef<HTMLDivElement>(null);
  const sending = useRef(false);
  const [life] = useState(() => new AbortController());
  const fileField = schema.fields.find((field) => field.name === 'profile_banner')!;
  const sizeLabel = new Intl.NumberFormat('pl-PL', { maximumFractionDigits: 1 }).format(
    data.banner.max_size / (1024 * 1024),
  );
  const errors = [
    ...(message ? [message] : []),
    ...(fileError ? [fileError] : []),
    ...schema.errors,
    ...schema.fields.flatMap((field) => field.errors),
  ];
  const preview = objectUrl || (remove ? data.banner.default_url : data.banner.url);
  const cropChanged = data.banner.custom && !remove && !sameBannerCrop(crop, data.banner.crop);
  const hasChanges = Boolean(file || remove || cropChanged);

  useEffect(() => () => life.abort(), [life]);
  useEffect(() => {
    if (!file) {
      setObjectUrl('');
      return;
    }
    const url = URL.createObjectURL(file);
    setObjectUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  useEffect(() => {
    if (
      message ||
      fileError ||
      schema.errors.length ||
      schema.fields.some((field) => field.errors.length)
    )
      alert.current?.focus();
  }, [message, fileError, schema]);

  function clearErrors() {
    setMessage('');
    setFileError('');
    setSchema((current) => ({
      ...current,
      errors: [],
      fields: current.fields.map((field) => ({ ...field, errors: [] })),
    }));
  }

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.currentTarget.files?.[0];
    if (!chosen || sending.current) return;
    clearErrors();
    if (
      (chosen.type && !imageTypes.has(chosen.type)) ||
      (!chosen.type && !/\.(png|jpe?g|webp)$/i.test(chosen.name))
    ) {
      event.currentTarget.value = '';
      setFileError('Wybierz obraz w formacie PNG, JPG lub WebP.');
      return;
    }
    if (!chosen.size || chosen.size > data.banner.max_size) {
      event.currentTarget.value = '';
      setFileError(
        chosen.size ? `Obraz może mieć maksymalnie ${sizeLabel} MB.` : 'Wybrany plik jest pusty.',
      );
      return;
    }
    setFile(chosen);
    setCrop(DEFAULT_BANNER_CROP);
    setPreviewReady(false);
    setRemove(false);
    setDirty(true);
  }

  function restoreDefault() {
    if (sending.current) return;
    clearErrors();
    setFile(null);
    setCrop(DEFAULT_BANNER_CROP);
    setPreviewReady(false);
    setRemove(data.banner.custom);
    setDirty(data.banner.custom);
    if (input.current) input.current.value = '';
  }

  function changeCrop(next: BannerCrop) {
    if (sending.current) return;
    setCrop(next);
    setDirty(Boolean(file || remove || !sameBannerCrop(next, data.banner.crop)));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending.current || fileError || !hasChanges || (!previewReady && !remove)) return;
    const body = new FormData();
    body.set('csrfmiddlewaretoken', token);
    if (file) body.set('profile_banner', file);
    else if (remove) body.set('remove_banner', '1');
    body.set('profile_banner_x', String(crop.x));
    body.set('profile_banner_y', String(crop.y));
    body.set('profile_banner_zoom', String(crop.zoom));
    sending.current = true;
    setPending(true);
    setMessage('');
    try {
      const result = await pageRequest<{ redirect: string }>(
        api,
        data.urls.update_profile_banner,
        token,
        life.signal,
        body,
      );
      flushSync(() => {
        setDirty(false);
        setPending(false);
      });
      location.assign(result.redirect);
    } catch (error) {
      if (life.signal.aborted) return;
      if (error instanceof PageError && error.data.type === 'account-profile')
        setSchema(((error.data as unknown as Page).data as ProfileData).banner_form);
      else setMessage(errorMessage(error));
      sending.current = false;
      setPending(false);
    }
  }

  return (
    <Modal
      title="Edytuj baner użytkownika"
      className="profile-banner-editor contacts-photo-editor-overlay"
      dialogClassName="contacts-photo-editor-dialog"
      dirty={dirty}
      pending={pending}
      onClose={onClose}
      header={(close) => (
        <header className="contacts-photo-editor-header">
          <strong>Edytuj baner użytkownika</strong>
          <button
            type="button"
            className="contacts-photo-editor-close"
            aria-label="Zamknij edycję banera"
            title="Zamknij"
            disabled={pending}
            onClick={close}
          >
            <Icon name="x" />
          </button>
        </header>
      )}
    >
      <form
        ref={form}
        className="tasks-modal__form profile-banner-form"
        method="post"
        action={data.urls.update_profile_banner}
        encType="multipart/form-data"
        noValidate
        onSubmit={submit}
        aria-busy={pending}
      >
        <input type="hidden" name="csrfmiddlewaretoken" value={token} />
        <input type="hidden" name="remove_banner" value={remove ? '1' : ''} />
        <input type="hidden" name="profile_banner_x" value={crop.x} />
        <input type="hidden" name="profile_banner_y" value={crop.y} />
        <input type="hidden" name="profile_banner_zoom" value={crop.zoom} />
        <input
          ref={input}
          id={fileField.id}
          type="file"
          name="profile_banner"
          accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"
          hidden
          disabled={pending}
          onChange={chooseFile}
        />
        <div className="tasks-modal__body">
          {errors.length ? (
            <div
              className="tasks-error-banner"
              id="profile-banner-errors"
              role="alert"
              ref={alert}
              tabIndex={-1}
            >
              <strong>Nie udało się zapisać banera:</strong>
              <ul>
                {errors.map((error, index) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <BannerCropper
            src={preview}
            crop={crop}
            editable={!remove && Boolean(file || data.banner.custom)}
            disabled={pending || !!fileError || !previewReady}
            onChange={changeCrop}
            onReadyChange={setPreviewReady}
            onImageError={() => {
              setPreviewReady(false);
              if (file || (data.banner.custom && !remove))
                setFileError('Nie udało się odczytać obrazu. Wybierz inny plik.');
            }}
          />
          <p className="profile-banner-help" id="profile-banner-help">
            {remove ? 'Po zapisaniu wróci domyślne tło profilu. ' : ''}
            PNG, JPG lub WebP · do {sizeLabel} MB · zalecany rozmiar 1600 × 400 px.
          </p>
        </div>
        <footer className="contacts-photo-editor-footer">
          <button
            type="button"
            className="contacts-photo-editor-secondary"
            disabled={pending || (!file && (!data.banner.custom || remove))}
            onClick={restoreDefault}
          >
            Usuń
          </button>
          <button
            type="button"
            className="contacts-photo-editor-secondary"
            disabled={pending}
            aria-describedby={
              'profile-banner-help' + (errors.length ? ' profile-banner-errors' : '')
            }
            aria-invalid={fileError || fileField.errors.length ? true : undefined}
            onClick={() => input.current?.click()}
          >
            Zmień
          </button>
          <button
            type="submit"
            className="contacts-photo-editor-primary"
            disabled={pending || !!fileError || !hasChanges || (!previewReady && !remove)}
          >
            {pending ? 'Zapisywanie…' : 'Zapisz'}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
