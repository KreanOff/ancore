import {
  type KeyboardEvent,
  type PointerEvent,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
} from 'react';
import { Icon } from '../shared/Icon';
import {
  bannerCropStyle,
  MAX_BANNER_ZOOM,
  MIN_BANNER_ZOOM,
  moveBannerCrop,
  normalizeBannerCrop,
  sameBannerCrop,
  type BannerCrop,
  type BannerSize,
} from './banner-crop';

interface Drag {
  pointerId: number;
  startX: number;
  startY: number;
  crop: BannerCrop;
  image: BannerSize;
  stage: BannerSize;
}

function stageSize(element: HTMLElement): BannerSize {
  const rect = element.getBoundingClientRect();
  // Exclude the border while retaining the scale applied by the shared shell.
  return {
    width: element.offsetWidth ? (rect.width * element.clientWidth) / element.offsetWidth : 0,
    height: element.offsetHeight ? (rect.height * element.clientHeight) / element.offsetHeight : 0,
  };
}

export default function BannerCropper({
  src,
  crop,
  editable,
  disabled,
  onChange,
  onImageError,
  onReadyChange,
}: {
  src: string;
  crop: BannerCrop;
  editable: boolean;
  disabled: boolean;
  onChange: (crop: BannerCrop) => void;
  onImageError: () => void;
  onReadyChange: (ready: boolean) => void;
}) {
  const stage = useRef<HTMLDivElement>(null);
  const image = useRef<HTMLImageElement>(null);
  const drag = useRef<Drag | null>(null);
  const [dragging, setDragging] = useState(false);
  const [loaded, setLoaded] = useState<(BannerSize & { src: string }) | null>(null);
  const natural = loaded?.src === src ? loaded : null;
  const ready = Boolean(natural);
  const active = editable && !disabled && ready;
  const id = useId();

  function readImage(element: HTMLImageElement) {
    if (image.current !== element || !element.naturalWidth || !element.naturalHeight) return;
    setLoaded({ src, width: element.naturalWidth, height: element.naturalHeight });
  }

  useLayoutEffect(() => {
    const element = image.current;
    if (element?.complete && element.naturalWidth) readImage(element);
  }, [src]);

  useEffect(() => onReadyChange(ready), [ready, onReadyChange]);
  useEffect(() => {
    setDragging(false);
    return () => {
      const current = drag.current;
      drag.current = null;
      if (current && stage.current?.hasPointerCapture(current.pointerId))
        stage.current.releasePointerCapture(current.pointerId);
    };
  }, [src, active]);

  function endDrag() {
    const current = drag.current;
    drag.current = null;
    setDragging(false);
    if (current && stage.current?.hasPointerCapture(current.pointerId))
      stage.current.releasePointerCapture(current.pointerId);
  }

  function startDrag(event: PointerEvent<HTMLDivElement>) {
    if (!active || !natural || event.button !== 0 || drag.current) return;
    event.preventDefault();
    event.currentTarget.focus({ preventScroll: true });
    drag.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      crop,
      image: natural,
      stage: stageSize(event.currentTarget),
    };
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragging(true);
  }

  function moveDrag(event: PointerEvent<HTMLDivElement>) {
    const current = drag.current;
    if (!active || !current || event.pointerId !== current.pointerId) return;
    const next = moveBannerCrop(
      current.crop,
      current.image,
      current.stage,
      event.clientX - current.startX,
      event.clientY - current.startY,
    );
    if (!sameBannerCrop(next, crop)) onChange(next);
  }

  function moveWithKeyboard(event: KeyboardEvent<HTMLDivElement>) {
    if (
      !active ||
      !natural ||
      !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)
    )
      return;
    event.preventDefault();
    endDrag();
    const amount = event.shiftKey ? 40 : 10;
    const next = moveBannerCrop(
      crop,
      natural,
      stageSize(event.currentTarget),
      event.key === 'ArrowLeft' ? -amount : event.key === 'ArrowRight' ? amount : 0,
      event.key === 'ArrowUp' ? -amount : event.key === 'ArrowDown' ? amount : 0,
    );
    if (!sameBannerCrop(next, crop)) onChange(next);
  }

  function zoom(value: number) {
    if (!active) return;
    endDrag();
    const next = normalizeBannerCrop({ ...crop, zoom: Number(value.toFixed(2)) });
    if (!sameBannerCrop(next, crop)) onChange(next);
  }

  return (
    <div className="profile-banner-cropper">
      <div className="profile-photo-crop-stage contacts-photo-editor-stage profile-banner-crop-surface">
        <div
          ref={stage}
          className={
            'profile-banner-preview profile-banner-crop-stage' +
            (editable ? ' is-editable' : '') +
            (dragging ? ' is-dragging' : '')
          }
          role={editable ? 'group' : undefined}
          aria-label={editable ? 'Kadr banera' : undefined}
          aria-describedby={editable ? id + '-instructions' : undefined}
          aria-disabled={editable ? !active : undefined}
          tabIndex={editable && !disabled ? 0 : undefined}
          onPointerDown={startDrag}
          onPointerMove={moveDrag}
          onPointerUp={endDrag}
          onPointerCancel={endDrag}
          onLostPointerCapture={endDrag}
          onKeyDown={moveWithKeyboard}
        >
          {editable ? (
            <img
              key={src}
              ref={image}
              className="profile-banner-image"
              src={src}
              alt="Podgląd banera użytkownika"
              draggable={false}
              style={bannerCropStyle(crop)}
              onLoad={(event) => readImage(event.currentTarget)}
              onError={(event) => {
                if (event.currentTarget !== image.current) return;
                setLoaded(null);
                onImageError();
              }}
            />
          ) : null}
        </div>
        {!editable ? (
          <div className="contacts-photo-editor-empty">Wybierz baner użytkownika</div>
        ) : null}
      </div>
      <p className="u-sr-only" id={id + '-instructions'}>
        Przeciągnij obraz, aby wybrać fragment. Użyj suwaka, aby przybliżyć. Obraz możesz też
        przesuwać strzałkami. Przytrzymaj Shift, aby przesuwać szybciej.
      </p>
      <div className="profile-photo-zoom-controls contacts-photo-editor-zoom">
        <button
          type="button"
          className="profile-photo-zoom-button"
          aria-label="Pomniejsz obraz"
          disabled={!active || crop.zoom <= MIN_BANNER_ZOOM}
          onClick={() => zoom(crop.zoom - 0.1)}
        >
          <Icon name="minus" />
        </button>
        <input
          id={id + '-zoom'}
          type="range"
          className="profile-photo-zoom-range"
          aria-label="Powiększenie obrazu"
          min={MIN_BANNER_ZOOM}
          max={MAX_BANNER_ZOOM}
          step={0.01}
          value={crop.zoom}
          aria-valuetext={`${Math.round(crop.zoom * 100)}%`}
          disabled={!active}
          onChange={(event) => zoom(Number(event.currentTarget.value))}
        />
        <button
          type="button"
          className="profile-photo-zoom-button"
          aria-label="Powiększ obraz"
          disabled={!active || crop.zoom >= MAX_BANNER_ZOOM}
          onClick={() => zoom(crop.zoom + 0.1)}
        >
          <Icon name="plus" />
        </button>
      </div>
    </div>
  );
}
