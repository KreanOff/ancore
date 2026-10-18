import type { ReactNode } from 'react';

type Illustration = 'spaces' | 'tasks' | 'people' | 'work';

export function EmptyState({
  title,
  description,
  illustration,
  src,
  className = '',
}: {
  title: ReactNode;
  description?: ReactNode;
  illustration?: Illustration;
  src?: string;
  className?: string;
}) {
  return (
    <div className={`tasks-empty-state tasks-empty-state--illustrated ${className}`} role="status">
      {src ? (
        <img
          className="tasks-empty-state__illustration"
          src={src}
          alt=""
          width={720}
          height={540}
          draggable={false}
        />
      ) : (
        <span
          className={`tasks-empty-state__illustration tasks-empty-state__illustration--${illustration || 'tasks'}`}
          aria-hidden="true"
        />
      )}
      <div className="tasks-empty-state__copy">
        <h2>{title}</h2>
        {description ? <p>{description}</p> : null}
      </div>
    </div>
  );
}
