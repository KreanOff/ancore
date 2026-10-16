import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import type { DirectoryData } from './types';
export default function Pagination({
  data,
  change,
}: {
  data: DirectoryData;
  change: (values: Record<string, string>) => void;
}) {
  const page = data.window;
  return (
    <div className="tasks-project-pagination tasks-project-pagination--toolbar">
      <nav
        className="tasks-project-pagination__pages tasks-project-pagination__pages--toolbar"
        aria-label={data.office ? 'Strony dokumentów' : 'Strony Dysku'}
      >
        {page.has_previous ? (
          <a
            className="tasks-project-pagination__button"
            href={page.previous_url}
            aria-label="Poprzednia strona"
          >
            <Icon name="chevron-left" />
          </a>
        ) : (
          <button
            type="button"
            className="tasks-project-pagination__button"
            disabled
            aria-label="Poprzednia strona"
          >
            <Icon name="chevron-left" />
          </button>
        )}
        <span
          className="tasks-project-pagination__summary tasks-project-pagination__summary--compact"
          aria-label={page.summary}
          aria-live="polite"
        >
          {page.compact_summary}
        </span>
        {page.has_next ? (
          <a
            className="tasks-project-pagination__button"
            href={page.next_url}
            aria-label="Następna strona"
          >
            <Icon name="chevron-right" />
          </a>
        ) : (
          <button
            type="button"
            className="tasks-project-pagination__button"
            disabled
            aria-label="Następna strona"
          >
            <Icon name="chevron-right" />
          </button>
        )}
      </nav>
      <Dropdown
        label="Liczba pozycji na stronie"
        className="tasks-project-pagination__size-control tasks-project-pagination__size-control--compact tasks-project-pagination__size-control--toolbar"
        menuClass="tasks-project-pagination__size-menu"
        triggerClassName="tasks-project-pagination__size-button tasks-project-pagination__size-button--compact tasks-project-pagination__size-button--toolbar"
        trigger={
          <>
            <Icon name="rows-3" />
            <span className="tasks-project-pagination__size-value">
              <strong>{page.page_size}</strong>
              <span>/ stronę</span>
            </span>
            <Icon name="chevron-down" />
          </>
        }
      >
        {(close) => (
          <>
            {page.page_size_options.map((size) => (
              <button
                key={size}
                type="button"
                role="menuitemradio"
                aria-checked={size === page.page_size}
                className={size === page.page_size ? 'is-active' : ''}
                onClick={() => {
                  close();
                  change({ page_size: String(size) });
                }}
              >
                {size}
              </button>
            ))}
          </>
        )}
      </Dropdown>
    </div>
  );
}
