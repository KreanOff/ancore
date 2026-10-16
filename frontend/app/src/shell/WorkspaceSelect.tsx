import { useLayoutEffect, useRef } from 'react';
import type { Inbox } from './types';
export default function WorkspaceSelect({
  choices,
  value,
  disabled,
  onChange,
}: {
  choices: Inbox['workplaces'];
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const latest = useRef(onChange);
  latest.current = onChange;
  useLayoutEffect(() => {
    const root = host.current!,
      select = document.createElement('select');
    select.className = 'form-select';
    select.setAttribute('aria-label', 'Workspace powiadomień');
    select.add(new Option('Wszystkie Workspace', ''));
    for (const choice of choices) {
      const option = new Option(choice.name, choice.id),
        template = document.createElement('template'),
        art = document.createElement('span');
      template.id = 'notification-workspace-' + choice.id;
      const avatar = choice.avatar;
      art.className = `profile-avatar space-avatar ${avatar.photo_url ? 'has-photo' : 'space-avatar-art ' + avatar.preset_class}`;
      art.setAttribute('aria-hidden', 'true');
      if (avatar.photo_url) {
        const image = document.createElement('img');
        image.src = avatar.photo_url;
        image.alt = '';
        art.append(image);
      }
      template.content.append(art);
      root.append(template);
      option.dataset.ancoreOptionPreview = template.id;
      select.add(option);
    }
    select.value = value;
    select.disabled = disabled;
    select.addEventListener('change', () => latest.current(select.value));
    root.append(select);
    window.AncoreCustomSelect?.refresh(root);
    return () => {
      window.AncoreCustomSelect?.closeAll();
      root.replaceChildren();
    };
  }, [choices, value, disabled]);
  return <div ref={host} className="react-notification-workspaces" />;
}
