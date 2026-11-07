export interface LoadMoreProps {
  loaded: number;
  total: number;
  hasMore: boolean;
  loading?: boolean;
  disabled?: boolean;
  error?: string;
  onLoad: () => void;
  label?: string;
}

export function LoadMore({
  loaded,
  total,
  hasMore,
  loading = false,
  disabled = false,
  error = '',
  onLoad,
  label = 'Wyniki',
}: LoadMoreProps) {
  if (!hasMore && total <= 20 && !loading && !error) return null;
  const locked = loading || disabled || !hasMore;
  const text = loading ? 'Wczytywanie…' : hasMore ? 'Pokaż więcej' : 'Wszystkie wyniki';
  return (
    <div className="app-load-more">
      <button
        type="button"
        className="tasks-filter-button work-list-more"
        aria-label={`${text}: ${label} (${loaded} / ${total})`}
        aria-disabled={locked}
        aria-busy={loading}
        onClick={() => {
          if (!locked) onLoad();
        }}
      >
        {text}
        <span className="work-list-more__count" aria-live="polite">
          ({loaded} / {total})
        </span>
      </button>
      {error ? (
        <div className="tasks-modal__errors work-list-more-error" role="alert">
          {error} Kliknij „Pokaż więcej”, aby ponowić.
        </div>
      ) : null}
    </div>
  );
}
