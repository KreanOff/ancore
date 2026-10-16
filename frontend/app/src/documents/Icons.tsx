// Geometry matches documents/includes/{file_icon_shape,folder_icon,drive_icon}.html.
import type { CSSProperties } from 'react';
export function FileIcon({ variant = 'generic' }: { variant?: string }) {
  return (
    <svg
      className={'documents-type-icon documents-type-icon--' + variant}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 64 64"
      width="24"
      height="24"
      aria-hidden="true"
      focusable="false"
    >
      <path
        className="documents-type-icon__paper"
        d="M22 3h20l16 16v36a6 6 0 0 1-6 6H22a6 6 0 0 1-6-6V9a6 6 0 0 1 6-6Z"
      />
      <path opacity=".45" d="M42 3v10a6 6 0 0 0 6 6h10Z" />
      <rect opacity=".35" x="24" y="21" width="18" height="3" rx="1.5" />
      <rect x="4" y="29" width="40" height="30" rx="7" />
      <g fill="#fff">
        {variant === 'word' ? (
          <>
            <rect x="12" y="36" width="24" height="4" rx="2" />
            <rect x="12" y="43" width="24" height="3" rx="1.5" opacity=".8" />
            <rect x="12" y="49" width="16" height="3" rx="1.5" opacity=".8" />
          </>
        ) : null}
        {variant === 'excel' ? (
          <>
            <path
              fillRule="evenodd"
              d="M14 35h20a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H14a2 2 0 0 1-2-2V37a2 2 0 0 1 2-2Zm1 6v3h5v-3Zm8 0v3h10v-3Zm-8 6v3h5v-3Zm8 0v3h10v-3Z"
            />
          </>
        ) : null}
        {variant === 'powerpoint' ? (
          <>
            <path d="M23 35a9 9 0 1 0 9 9h-9Z" />
            <path opacity=".65" d="M26 33v8h8a8 8 0 0 0-8-8Z" />
          </>
        ) : null}
        {variant === 'pdf' ? (
          <>
            <path
              fillRule="evenodd"
              d="M10 38h4a4 4 0 0 1 0 8h-1v4h-3Zm3 3v2h1a1 1 0 0 0 0-2Zm7-3h4a6 6 0 0 1 0 12h-4Zm3 3v6h1a3 3 0 0 0 0-6Z"
            />
            <path d="M32 38h7v3h-4v2h3v3h-3v4h-3Z" />
          </>
        ) : null}
        {variant === 'image' ? (
          <>
            <circle cx="30" cy="39" r="3" />
            <path d="m11 52 9-13 7 9 4-5 7 9Z" />
          </>
        ) : null}
        {variant === 'archive' ? (
          <>
            <path d="M20 29h4v5h-4Zm4 5h4v5h-4Zm-4 5h4v5h-4Z" />
            <path
              fillRule="evenodd"
              d="M20 44h8a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-8a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2Zm1 4v4h6v-4Z"
            />
          </>
        ) : null}
        {variant === 'audio' ? (
          <>
            <path d="M20 36v11a5 4 0 1 0 3 3V41l9-2v6a5 4 0 1 0 3 3V33Z" />
          </>
        ) : null}
        {variant === 'video' ? (
          <>
            <path d="M18 36a2 2 0 0 1 3-1.7l13 8a2 2 0 0 1 0 3.4l-13 8a2 2 0 0 1-3-1.7Z" />
          </>
        ) : null}
        {variant === 'code' ? (
          <>
            <path d="m18 36-8 8 8 8 2.5-2.5L15 44l5.5-5.5Zm12 0-2.5 2.5L33 44l-5.5 5.5L30 52l8-8Z" />
          </>
        ) : null}
        {variant === 'board' ? (
          <>
            <rect x="12" y="36" width="9" height="9" rx="2" />
            <circle cx="31" cy="40.5" r="4.5" opacity=".75" />
            <path d="m24 44 7 10H17Z" />
          </>
        ) : null}
        {variant === 'text' ? (
          <>
            <path d="M13 36h22v4h-9v13h-4V40h-9Z" />
          </>
        ) : null}
        {![
          'word',
          'excel',
          'powerpoint',
          'pdf',
          'image',
          'archive',
          'audio',
          'video',
          'code',
          'board',
          'text',
        ].includes(variant) ? (
          <>
            <rect x="15" y="36" width="18" height="3" rx="1.5" />
            <rect x="15" y="43" width="18" height="3" rx="1.5" />
            <rect x="15" y="50" width="11" height="3" rx="1.5" />
          </>
        ) : null}
      </g>
    </svg>
  );
}

export function DriveIcon({ color = '#4285d4' }: { color?: string }) {
  const style = { '--documents-icon-color': color } as CSSProperties;
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 64 64"
      width="24"
      height="24"
      style={style}
      className={'documents-drive-icon'}
      aria-hidden="true"
      focusable="false"
    >
      <rect
        fill="#4285d4"
        style={{ fill: 'var(--documents-icon-color)' }}
        x="3"
        y="10"
        width="58"
        height="46"
        rx="10"
      />
      <path fill="#fff" opacity=".7" d="M13 10h38a10 10 0 0 1 10 10v18H3V20a10 10 0 0 1 10-10Z" />
      <rect
        fill="#4285d4"
        style={{ fill: 'var(--documents-icon-color)' }}
        opacity=".35"
        x="12"
        y="18"
        width="40"
        height="13"
        rx="4"
      />
      <rect fill="#fff" x="12" y="44" width="20" height="4" rx="2" />
      <circle fill="#fff" opacity=".55" cx="43" cy="46" r="2" />
      <circle fill="#fff" cx="51" cy="46" r="2.5" />
    </svg>
  );
}

export function FolderIcon({
  color = '#ffd855',
  filled = false,
}: {
  color?: string;
  filled?: boolean;
}) {
  const style = {
    '--documents-icon-color': color,
    '--documents-folder-tab':
      color === '#ffd855' ? '#ffb41f' : `color-mix(in srgb, ${color} 82%, #000)`,
  } as CSSProperties;
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 64 64"
      width="24"
      height="24"
      style={style}
      className={'documents-folder-icon documents-folder-icon--' + (filled ? 'filled' : 'empty')}
      aria-hidden="true"
      focusable="false"
    >
      {filled ? (
        <>
          <path
            fill="#ffb41f"
            style={{ fill: 'var(--documents-folder-tab, #ffb41f)' }}
            d="M4 17a6 6 0 0 1 6-6h12a6 6 0 0 1 4.2 1.8l4.2 4.2H54a6 6 0 0 1 6 6v27H4Z"
          />
          <rect fill="#fff" x="14" y="13" width="39" height="35" rx="4" />
          <rect
            fill="#ffd855"
            style={{ fill: 'var(--documents-icon-color)' }}
            opacity=".35"
            x="14"
            y="13"
            width="39"
            height="35"
            rx="4"
          />
          <rect fill="#fff" x="9" y="20" width="40" height="30" rx="4" />
          <rect
            fill="#ffb41f"
            style={{ fill: 'var(--documents-folder-tab, #ffb41f)' }}
            opacity=".4"
            x="16"
            y="25"
            width="23"
            height="3"
            rx="1.5"
          />
          <path
            fill="#ffd855"
            style={{ fill: 'var(--documents-icon-color)' }}
            d="M7 33h50a5 5 0 0 1 5 5.6l-2.2 13a6 6 0 0 1-6 5.4H10.2a6 6 0 0 1-6-5.4L2 38.6A5 5 0 0 1 7 33Z"
          />
          <rect fill="#fff" opacity=".65" x="11" y="40" width="19" height="4" rx="2" />
        </>
      ) : (
        <>
          <path
            fill="#ffb41f"
            style={{ fill: 'var(--documents-folder-tab, #ffb41f)' }}
            d="M4 17a6 6 0 0 1 6-6h13a6 6 0 0 1 4.2 1.8l4.2 4.2H54a6 6 0 0 1 6 6v28a6 6 0 0 1-6 6H10a6 6 0 0 1-6-6Z"
          />
          <path
            fill="#ffd855"
            style={{ fill: 'var(--documents-icon-color)' }}
            d="M4 25h56v26a6 6 0 0 1-6 6H10a6 6 0 0 1-6-6Z"
          />
          <rect fill="#fff" opacity=".65" x="12" y="33" width="19" height="4" rx="2" />
        </>
      )}
    </svg>
  );
}
