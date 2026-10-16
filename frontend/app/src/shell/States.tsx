import { Icon } from '../shared/Icon';
export function PanelState({
  icon,
  title,
  children,
  retry,
}: {
  icon: string;
  title: string;
  children: React.ReactNode;
  retry?: () => void;
}) {
  return (
    <div className="global-search-state">
      <span className="global-search-state__icon">
        <Icon name={icon} />
      </span>
      <h3>{title}</h3>
      <p>{children}</p>
      {retry ? (
        <button type="button" className="global-search-state__retry" onClick={retry}>
          Spróbuj ponownie
        </button>
      ) : null}
    </div>
  );
}
export function LoadingRows() {
  return (
    <div className="global-search-loading" aria-hidden="true">
      {Array.from({ length: 6 }, (_, i) => (
        <span className="global-search-loading__row" key={i}>
          <span />
          <span />
        </span>
      ))}
    </div>
  );
}
