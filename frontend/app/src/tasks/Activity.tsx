import { Avatar } from '../shared/Avatar';
import { Icon } from '../shared/Icon';
import type { Activity, FileData } from './types';
export function FileIcon({ type }: { type: string }) {
  return (
    <span className={`attachment-icon attachment-icon--lg ${type}`}>
      <Icon
        name={
          type === 'image'
            ? 'file-image'
            : type === 'archive'
              ? 'file-archive'
              : type === 'document' || type === 'pdf'
                ? 'file-text'
                : 'file'
        }
      />
    </span>
  );
}
export function ActivityItem({ item }: { item: Activity }) {
  const m = item.metadata;
  return (
    <article
      className={`tasks-issue-feed-item ${item.kind === 'comment' ? 'tasks-issue-feed-item--comment' : ''}`}
    >
      <Avatar data={item.avatar} className="tasks-issue-avatar" />
      <div className="tasks-issue-feed-body">
        <p>
          <strong>{item.actor}</strong>
          {item.kind !== 'comment' ? ' ' + item.message + ' ' : ' '}
          <time dateTime={item.created_at}>
            {new Date(item.created_at).toLocaleString('pl-PL', {
              timeZone: 'Europe/Warsaw',
              day: '2-digit',
              month: '2-digit',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </time>
        </p>
        {item.kind === 'comment' ? (
          <>
            <div className="tasks-issue-chat-message" style={{ whiteSpace: 'pre-wrap' }}>
              {item.message}
            </div>
            {item.files.length ? (
              <div className="tasks-comment-images" aria-label="Załączniki w wiadomości">
                {item.files.map((file) =>
                  file.image ? (
                    <a
                      className="tasks-comment-image"
                      key={file.id}
                      href={file.url}
                      target="_blank"
                      rel="noopener"
                      title={`Otwórz zdjęcie: ${file.name}`}
                    >
                      <img src={file.url} alt={file.name} loading="lazy" />
                    </a>
                  ) : (
                    <a
                      key={file.id}
                      className="tasks-attachment-card tasks-comment-file is-link"
                      href={file.url}
                      download={file.name}
                    >
                      <span className="tasks-attachment-info">
                        <FileIcon type={file.type_class} />
                        <span className="tasks-attachment-details">
                          <span className="tasks-attachment-name">{file.name}</span>
                          <span className="tasks-attachment-size">{file.size}</span>
                        </span>
                      </span>
                      <Icon name="download" />
                    </a>
                  ),
                )}
              </div>
            ) : null}
          </>
        ) : m.changes?.length ? (
          m.changes.map((change, index) => (
            <p className="tasks-issue-feed-note tasks-issue-change-line" key={index}>
              {change.field.charAt(0).toUpperCase() + change.field.slice(1)}:{' '}
              {change.from_label ? (
                <>
                  <strong>{change.from_label}</strong> →{' '}
                </>
              ) : null}
              <strong>{change.to_label}</strong>
            </p>
          ))
        ) : m.from_label || m.to_label ? (
          <p className="tasks-issue-feed-note tasks-issue-change-line">
            {m.from_label ? (
              <>
                <strong>{m.from_label}</strong> →{' '}
              </>
            ) : null}
            <strong>{m.to_label}</strong>
          </p>
        ) : m.old_status_label || m.new_status_label ? (
          <p className="tasks-issue-feed-note tasks-issue-change-line">
            <strong>{m.old_status_label}</strong> → <strong>{m.new_status_label}</strong>
          </p>
        ) : m.fields ? (
          <p className="tasks-issue-feed-note">
            Zmienione pola: <strong>{m.fields.join(', ')}</strong>
          </p>
        ) : item.action === 'created' && m.title ? (
          <p className="tasks-issue-feed-note">
            Tytuł: <strong>{m.title}</strong>
          </p>
        ) : m.count ? (
          <p className="tasks-issue-feed-note">
            Liczba: <strong>{m.count}</strong>
          </p>
        ) : m.subtask_title ? (
          <p className="tasks-issue-feed-note">
            <strong>{m.subtask_title}</strong>
          </p>
        ) : null}
      </div>
    </article>
  );
}
export function Attachments({
  files,
  editable,
  remove,
}: {
  files: FileData[];
  editable: boolean;
  remove: (file: FileData) => void;
}) {
  return files.length ? (
    <section className="tasks-issue-attachments" aria-label="Załączniki">
      <div className="tasks-attachments-grid">
        {files.map((file) => (
          <div className="tasks-attachment-card" key={file.id}>
            <a className="tasks-attachment-info" href={file.url}>
              <FileIcon type={file.type_class} />
              <span className="tasks-attachment-details">
                <span className="tasks-attachment-name">{file.name}</span>
                <span className="tasks-attachment-size">{file.size}</span>
              </span>
            </a>
            {editable ? (
              <button
                type="button"
                className="tasks-delete-attach-btn"
                aria-label={`Usuń załącznik ${file.name}`}
                onClick={() => remove(file)}
              >
                <Icon name="trash-2" />
              </button>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  ) : null;
}
