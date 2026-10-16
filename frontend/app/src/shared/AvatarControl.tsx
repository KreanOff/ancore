import { useLayoutEffect, useRef } from 'react';
import type { FormSchema } from '../forms/FormDialog';
import type { AvatarData } from './Avatar';
export interface AvatarForm extends FormSchema {
  automatic_avatar: AvatarData;
}
// The existing canvas cropper owns this DOM island, including its nested dialogs.
const cropMarkup = `<div class="contacts-photo-editor-overlay" role="dialog" aria-modal="true" aria-label="Edytuj logo miejsca pracy" hidden data-profile-photo-modal>
    <div class="contacts-photo-editor-dialog">
        <header class="contacts-photo-editor-header">
            <strong>Edytuj logo miejsca pracy</strong>
            <button type="button" class="contacts-photo-editor-close" aria-label="Zamknij edycję obrazu" title="Zamknij" data-profile-photo-close>
                <i data-icon="x" aria-hidden="true"></i>
            </button>
        </header>

        <div class="profile-photo-cropper contacts-photo-editor-cropper" data-profile-photo-cropper>
            <div class="profile-photo-crop-stage contacts-photo-editor-stage" data-profile-photo-crop-stage>
                <canvas class="profile-photo-crop-canvas"
                        width="640"
                        height="640"
                        aria-label="Kadr logo miejsca pracy"
                        data-profile-photo-canvas></canvas>
                <div class="contacts-photo-editor-empty" data-profile-photo-empty>
                    <span>Wybierz logo miejsca pracy</span>
                </div>
            </div>
            <div class="profile-photo-zoom-controls contacts-photo-editor-zoom">
                <button type="button"
                        class="profile-photo-zoom-button"
                        aria-label="Pomniejsz obraz"
                        title="Pomniejsz obraz"
                        data-profile-photo-zoom-out>
                    <i data-icon="minus" aria-hidden="true"></i>
                </button>
                <input type="range"
                       class="profile-photo-zoom-range"
                       min="1"
                       max="4"
                       step="0.01"
                       value="1"
                       aria-label="Powiększenie obrazu"
                       data-profile-photo-zoom>
                <button type="button"
                        class="profile-photo-zoom-button"
                        aria-label="Powiększ obraz"
                        title="Powiększ obraz"
                        data-profile-photo-zoom-in>
                    <i data-icon="plus" aria-hidden="true"></i>
                </button>
            </div>
        </div>

        <footer class="contacts-photo-editor-footer">
            <button type="button" class="contacts-photo-editor-secondary" data-profile-photo-remove>Usuń</button>
            <button type="button" class="contacts-photo-editor-secondary" data-profile-photo-change>Zmień</button>
            <button type="button" class="contacts-photo-editor-primary" data-profile-photo-save>Zapisz</button>
        </footer>
    </div>
</div>
`;
export default function AvatarControl({
  schema,
  formId,
  create = false,
  account = false,
}: {
  schema: AvatarForm;
  formId: string;
  create?: boolean;
  account?: boolean;
}) {
  const host = useRef<HTMLDivElement>(null);
  const initial = useRef(schema);
  useLayoutEffect(() => {
    const root = host.current!,
      data = initial.current,
      owner = root.closest('form')!;
    const fields = data.fields;
    const value = (name: string) => {
      const v = fields.find((f) => f.name === name)?.value;
      return Array.isArray(v) ? v[0] || '' : v || '';
    };
    root.innerHTML = `<div class="profile-photo-control profile-photo-control--modal workplace-photo-control" data-profile-photo-editor>
   <button type="button" class="profile-photo-preview-button" aria-label="Wybierz awatar Workspace" title="Wybierz awatar Workspace" data-workplace-avatar-open aria-haspopup="dialog" aria-expanded="false"><span class="profile-avatar profile-page-avatar profile-avatar--workplace" data-profile-photo-preview aria-hidden="true"></span></button>
   <template data-profile-photo-fallback></template><button type="button" class="profile-photo-button" data-workplace-avatar-open aria-haspopup="dialog" aria-expanded="false"></button>
   <div class="tasks-modal app-modal-panel app-modal-panel--compact tasks-form-modal workplace-avatar-modal" role="dialog" aria-modal="true" aria-label="Wybierz awatar" aria-hidden="true" data-workplace-avatar-modal>
    <div class="tasks-modal__dialog"><div class="tasks-modal__form"><header class="tasks-modal__header"><h2>Wybierz awatar</h2><button type="button" class="tasks-modal__close" aria-label="Zamknij" data-close-modal></button></header>
     <div class="tasks-modal__body"><div class="space-avatar-picker" data-workplace-avatar-picker>
      <fieldset class="space-avatar-presets"><legend>Wybierz gotowy awatar</legend><div class="space-avatar-grid"></div><label class="space-avatar-auto"><input type="radio" name="avatar" value="auto"> Automatyczny awatar</label></fieldset>
      <div class="space-avatar-upload" data-workplace-avatar-drop><label class="space-avatar-auto"><input type="radio" name="avatar" value="upload"> Własny obraz</label><div class="space-avatar-upload__content"><span class="profile-avatar space-avatar space-avatar--picker has-photo" data-workplace-avatar-upload-preview hidden></span><div class="space-avatar-upload__actions"><button type="button" class="btn btn-secondary" data-workplace-avatar-upload>Wybierz obraz</button><input type="file" name="workplace_photo" class="profile-photo-input" accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp" hidden><input type="hidden" name="workplace_photo_crop" data-profile-photo-crop-input><input type="hidden" name="workplace_photo_remove" data-profile-photo-remove-input><small>lub przeciągnij i upuść tutaj · PNG, JPG, WebP · do 5 MB</small></div></div><div class="tasks-modal__errors" role="alert" data-workplace-avatar-error hidden></div></div>
     </div></div><footer class="tasks-modal__footer"><button type="button" class="btn btn-secondary" data-close-modal>Anuluj</button><button type="button" class="tasks-modal__submit" data-workplace-avatar-save>Zapisz</button></footer>
    </div></div></div></div>`;
    const editor = root.querySelector<HTMLElement>('[data-profile-photo-editor]')!;
    const modal = root.querySelector<HTMLElement>('[data-workplace-avatar-modal]')!;
    modal.id = formId + '-avatar-modal';
    modal.insertAdjacentHTML('beforeend', cropMarkup);
    editor.querySelector<HTMLButtonElement>('.profile-photo-button')!.textContent = create
      ? 'Dodaj'
      : 'Zmień';
    editor
      .querySelectorAll('[data-workplace-avatar-open]')
      .forEach((e) => e.setAttribute('aria-controls', modal.id));
    if (account) {
      root.querySelector<HTMLElement>('[data-workplace-avatar-picker]')!.dataset.avatarArtClass =
        'user-avatar-art';
      editor.classList.remove('workplace-photo-control');
      editor
        .querySelector('.profile-photo-preview-button')!
        .setAttribute('aria-label', 'Zmień awatar użytkownika');
      editor
        .querySelector('.profile-photo-preview-button')!
        .setAttribute('title', 'Zmień awatar użytkownika');
      editor
        .querySelector('[data-profile-photo-preview]')!
        .classList.replace('profile-avatar--workplace', 'profile-avatar--user');
      root.querySelectorAll<HTMLInputElement>('input[name^=workplace_photo]').forEach((input) => {
        input.name = input.name.replace('workplace_photo', 'profile_photo');
      });
      const crop = root.querySelector<HTMLElement>('[data-profile-photo-modal]')!;
      crop.setAttribute('aria-label', 'Edytuj zdjęcie użytkownika');
      crop.querySelector('strong')!.textContent = 'Edytuj zdjęcie użytkownika';
      crop.querySelector('canvas')!.setAttribute('aria-label', 'Kadr zdjęcia użytkownika');
      crop.querySelector('[data-profile-photo-empty] span')!.textContent =
        'Wybierz zdjęcie użytkownika';
    }
    editor.dataset.profilePhotoUrl = data.current_avatar?.photo_url || '';
    root.querySelector<HTMLElement>('[data-workplace-avatar-picker]')!.dataset.automaticAvatar =
      data.automatic_avatar.preset_class || '';
    const grid = root.querySelector('.space-avatar-grid')!;
    for (const option of data.avatars || []) {
      const label = document.createElement('label'),
        radio = document.createElement('input'),
        art = document.createElement('span'),
        text = document.createElement('span');
      label.className = 'space-avatar-option';
      label.title = option.label;
      radio.type = 'radio';
      radio.className = 'u-sr-only';
      radio.name = 'avatar';
      radio.value = option.key;
      art.className =
        'profile-avatar space-avatar space-avatar--picker ' +
        (account ? 'user-avatar-art ' : 'space-avatar-art ') +
        option.preset_class;
      art.setAttribute('aria-hidden', 'true');
      text.className = 'u-sr-only';
      text.textContent = option.label;
      label.append(radio, art, text);
      grid.append(label);
    }
    root.querySelectorAll<HTMLInputElement>('input').forEach((input) => {
      input.setAttribute('form', formId);
      if (input.type === 'radio') input.checked = input.value === (value('avatar') || 'auto');
      else if (input.type === 'hidden') input.value = value(input.name);
    });
    window.AncoreIcons?.render(root);
    window.AncorePhotoEditors?.init(root);
    window.AncoreWorkplaceAvatars?.init(root);
    return () => {
      window.AncoreWorkplaceAvatars?.dispose(owner);
      (editor as PhotoEditor).profilePhotoEditorApi?.destroy();
      root.replaceChildren();
    };
  }, [formId, create, account]);
  return <div className="react-workspace-avatar" ref={host} />;
}
interface PhotoEditor extends HTMLElement {
  profilePhotoEditorApi?: { destroy(): void };
}
