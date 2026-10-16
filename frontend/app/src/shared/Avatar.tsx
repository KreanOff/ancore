import { type CSSProperties } from 'react';
import { Icon } from './Icon';
export interface AvatarData {
  photo_url?: string;
  preset_class?: string;
  color_class?: string;
  background_color?: string;
  foreground_color?: string;
}
export function Avatar({
  data,
  space = false,
  className = '',
}: {
  data: AvatarData;
  space?: boolean;
  className?: string;
}) {
  return (
    <span
      className={`profile-avatar ${space ? 'space-avatar' : 'profile-avatar--user'} ${className} ${data.color_class || ''} ${data.photo_url ? 'has-photo' : `${space ? 'space-avatar-art' : 'user-avatar-art'} ${data.preset_class || ''}`}`}
      style={
        {
          '--profile-avatar-bg': data.background_color,
          '--profile-avatar-fg': data.foreground_color,
        } as CSSProperties
      }
      aria-hidden="true"
      data-space-avatar={space ? '' : undefined}
    >
      {data.photo_url ? (
        <img src={data.photo_url} alt="" draggable={false} />
      ) : !data.preset_class && !space ? (
        <Icon name="user-round" />
      ) : null}
    </span>
  );
}
