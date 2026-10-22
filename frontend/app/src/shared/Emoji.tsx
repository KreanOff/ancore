import { Icon } from './Icon';

export type EmojiArt =
  | { url: string; position: string; icon?: never }
  | { icon: string; url?: never; position?: never };
export interface EmojiValue {
  value: string;
  label: string;
  art: EmojiArt;
}
export function Emoji({
  value,
  art,
  className = '',
}: {
  value: string;
  art?: EmojiArt;
  className?: string;
}) {
  const icon = art?.icon || (value === 'layout-dashboard' ? 'layout-dashboard' : undefined);
  return (
    <span
      className={`ancore-emoji ${className}`}
      aria-hidden="true"
      style={
        art?.url
          ? { backgroundImage: `url("${art.url}")`, backgroundPosition: art.position }
          : undefined
      }
    >
      {icon ? <Icon name={icon} /> : art ? null : value}
    </span>
  );
}
