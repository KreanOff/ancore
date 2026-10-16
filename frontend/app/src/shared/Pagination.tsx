import { Icon } from './Icon';
export interface PaginationData {
  page: number;
  count: number;
  start: number;
  end: number;
  previous: string;
  next: string;
  pages: { label: string; url: string; current: boolean }[];
}
export function Pagination({ data }: { data: PaginationData | null }) {
  if (!data) return null;
  return (
    <div className="tasks-project-pagination work-pagination">
      <span className="tasks-project-pagination__summary" aria-live="polite">
        {data.start}–{data.end} z {data.count}
      </span>
      <nav className="tasks-project-pagination__pages" aria-label="Strony wyników">
        {data.previous ? (
          <a
            className="tasks-project-pagination__button"
            href={data.previous}
            aria-label="Poprzednia strona"
          >
            <Icon name="chevron-left" />
          </a>
        ) : (
          <button
            type="button"
            className="tasks-project-pagination__button"
            aria-label="Poprzednia strona"
            disabled
          >
            <Icon name="chevron-left" />
          </button>
        )}
        {data.pages.map((page, index) =>
          !page.url ? (
            <span key={index} className="tasks-project-pagination__ellipsis" aria-hidden="true">
              {page.label}
            </span>
          ) : page.current ? (
            <span
              key={index}
              className="tasks-project-pagination__button is-active"
              aria-current="page"
              aria-label={`Strona ${page.label}`}
            >
              {page.label}
            </span>
          ) : (
            <a
              key={index}
              className="tasks-project-pagination__button"
              href={page.url}
              aria-label={`Strona ${page.label}`}
            >
              {page.label}
            </a>
          ),
        )}
        {data.next ? (
          <a
            className="tasks-project-pagination__button"
            href={data.next}
            aria-label="Następna strona"
          >
            <Icon name="chevron-right" />
          </a>
        ) : (
          <button
            type="button"
            className="tasks-project-pagination__button"
            aria-label="Następna strona"
            disabled
          >
            <Icon name="chevron-right" />
          </button>
        )}
      </nav>
    </div>
  );
}
