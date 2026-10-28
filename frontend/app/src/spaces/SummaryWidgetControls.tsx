import type { CSSProperties } from 'react';
import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import {
  GRID_COLUMNS,
  GRID_GAP,
  MAX_GRID_ROWS,
  MAX_WIDGET_HEIGHT,
  ROW_HEIGHT,
  type SummaryWidget,
  type WidgetDirection,
  type WidgetSize,
} from './summaryLayout';

export function SummaryWidgetControls({
  widget,
  layout,
  label,
  minWidth,
  minHeight,
  disabled,
  stacked = false,
  onMove,
  onResize,
  onRemove,
}: {
  widget: SummaryWidget;
  layout: SummaryWidget[];
  label: string;
  minWidth: number;
  minHeight: number;
  disabled: boolean;
  stacked?: boolean;
  onMove: (direction: WidgetDirection) => void;
  onResize: (size: WidgetSize) => void;
  onRemove: () => void;
}) {
  const rows = Math.max(8, ...layout.map((item) => item.y + item.h));
  const ordered = [...layout].sort((a, b) => a.y - b.y || a.x - b.x);
  const position = ordered.findIndex((item) => item.id === widget.id);
  const directions: { direction: WidgetDirection; label: string; icon: string; atEdge: boolean }[] =
    [
      {
        direction: 'up',
        label: 'Przesuń w górę',
        icon: 'arrow-up',
        atEdge: stacked ? position === 0 : widget.y === 0,
      },
      { direction: 'left', label: 'Przesuń w lewo', icon: 'arrow-left', atEdge: widget.x === 0 },
      {
        direction: 'down',
        label: 'Przesuń w dół',
        icon: 'arrow-down',
        atEdge: stacked ? position === ordered.length - 1 : widget.y + widget.h >= MAX_GRID_ROWS,
      },
      {
        direction: 'right',
        label: 'Przesuń w prawo',
        icon: 'arrow-right',
        atEdge: widget.x + widget.w >= GRID_COLUMNS,
      },
    ];
  const presets = [
    { width: Math.max(3, minWidth), label: minWidth > 3 ? '1/3' : '1/4' },
    { width: 6, label: '1/2' },
    { width: GRID_COLUMNS, label: 'Cały wiersz' },
  ];
  const height = widget.h * ROW_HEIGHT + (widget.h - 1) * GRID_GAP;
  return (
    <Dropdown
      label={`Opcje gadżetu: ${label}`}
      disabled={disabled}
      searchable={false}
      positioning="fixed"
      role="dialog"
      menuClass="work-summary-controls-menu"
      triggerClassName="tasks-filter-button work-summary-widget-menu"
      trigger={<Icon name="menu" />}
    >
      {(close) => (
        <>
          <header className="work-summary-controls-heading">
            <strong>{label}</strong>
            <span className="work-caption">
              Podgląd na żywo. Zmiany zatwierdzisz przez „Zapisz układ”.
            </span>
          </header>
          <div className="work-summary-controls-position">
            <div className="work-summary-controls-location">
              <span className="work-summary-control-label">Pozycja</span>
              <div
                className={`work-summary-direction-pad ${stacked ? 'is-stacked' : ''}`}
                role="group"
                aria-label="Pozycja gadżetu"
              >
                {directions
                  .filter(
                    (item) => !stacked || item.direction === 'up' || item.direction === 'down',
                  )
                  .map((item) => (
                    <button
                      key={item.direction}
                      type="button"
                      className={`tasks-filter-button work-summary-direction work-summary-direction--${item.direction}`}
                      aria-label={item.label}
                      title={item.label}
                      disabled={disabled || item.atEdge}
                      onClick={() => onMove(item.direction)}
                    >
                      <Icon name={item.icon} />
                    </button>
                  ))}
              </div>
            </div>
            <div className="work-summary-layout-preview" aria-hidden="true">
              {layout.map((item) => (
                <span
                  key={item.id}
                  className={item.id === widget.id ? 'is-selected' : ''}
                  style={
                    {
                      left: `${(item.x * 100) / GRID_COLUMNS}%`,
                      top: `${(item.y * 100) / rows}%`,
                      width: `${(item.w * 100) / GRID_COLUMNS}%`,
                      height: `${(item.h * 100) / rows}%`,
                    } as CSSProperties
                  }
                />
              ))}
            </div>
          </div>
          <section className="work-summary-controls-size" aria-label="Rozmiar gadżetu">
            <span className="work-summary-control-label">Rozmiar</span>
            <label className="work-summary-size-control">
              <span>
                Szerokość <output>{Math.round((widget.w * 100) / GRID_COLUMNS)}% pulpitu</output>
              </span>
              <input
                type="range"
                aria-label="Szerokość gadżetu"
                min={minWidth}
                max={GRID_COLUMNS}
                step={1}
                value={widget.w}
                aria-valuetext={`${Math.round((widget.w * 100) / GRID_COLUMNS)}% szerokości pulpitu`}
                disabled={disabled}
                onChange={(event) => onResize({ w: Number(event.target.value) })}
              />
            </label>
            <div
              className="work-summary-width-presets"
              role="group"
              aria-label="Szybki wybór szerokości"
            >
              {presets.map((preset) => (
                <button
                  key={preset.width}
                  type="button"
                  className={`tasks-filter-button ${widget.w === preset.width ? 'is-active' : ''}`}
                  aria-label={`Szerokość: ${preset.label} pulpitu`}
                  aria-pressed={widget.w === preset.width}
                  disabled={disabled}
                  onClick={() => onResize({ w: preset.width })}
                >
                  <span className="work-summary-width-preview" aria-hidden="true">
                    <span style={{ width: `${(preset.width * 100) / GRID_COLUMNS}%` }} />
                  </span>
                  {preset.label}
                </button>
              ))}
            </div>
            <label className="work-summary-size-control">
              <span>
                Wysokość <output>{height} px</output>
              </span>
              <input
                type="range"
                aria-label="Wysokość gadżetu"
                min={minHeight}
                max={Math.min(MAX_WIDGET_HEIGHT, MAX_GRID_ROWS - widget.y)}
                step={1}
                value={widget.h}
                aria-valuetext={`${height} pikseli wysokości`}
                disabled={disabled}
                onChange={(event) => onResize({ h: Number(event.target.value) })}
              />
            </label>
            <p className="work-caption work-summary-size-mobile-note">
              Na telefonie kafelki dopasowują się do ekranu. Rozmiar dotyczy widoku na komputerze.
            </p>
          </section>
          <footer className="work-summary-controls-footer">
            <button
              type="button"
              className="tasks-row-action"
              disabled={disabled}
              onClick={() => {
                close();
                onRemove();
              }}
            >
              <Icon name="trash-2" />
              Usuń gadżet
            </button>
            <button type="button" className="tasks-filter-button" onClick={close}>
              Zamknij
            </button>
          </footer>
        </>
      )}
    </Dropdown>
  );
}
