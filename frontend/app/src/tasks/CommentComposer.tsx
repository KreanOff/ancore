import { type ClipboardEvent, type DragEvent, useEffect, useRef, useState } from 'react';
import { Icon } from '../shared/Icon';
import type { TaskData } from './types';
type Mention = { user_id: number; start: number; end: number };
export default function CommentComposer({
  data,
  pending,
  send,
}: {
  data: TaskData;
  pending: boolean;
  send: (body: FormData) => Promise<boolean>;
}) {
  const [text, setText] = useState(data.comment_draft),
    [files, setFiles] = useState<File[]>([]),
    [error, setError] = useState(''),
    [mentions, setMentions] = useState<Mention[]>([]),
    [query, setQuery] = useState<{ start: number; end: number; value: string } | null>(null),
    [active, setActive] = useState(0);
  const input = useRef<HTMLTextAreaElement>(null),
    picker = useRef<HTMLInputElement>(null),
    life = useRef(true);
  useEffect(
    () => () => {
      life.current = false;
    },
    [],
  );
  const suggestions = query
    ? data.mentions
        .filter((person) =>
          (person.label + ' ' + person.email + ' ' + person.username)
            .toLocaleLowerCase('pl')
            .includes(query.value.toLocaleLowerCase('pl')),
        )
        .slice(0, 8)
    : [];
  function moveMentions(previous: string, value: string, current: Mention[]) {
    const before = Array.from(previous),
      after = Array.from(value);
    let start = 0,
      suffix = 0;
    while (start < before.length && start < after.length && before[start] === after[start]) start++;
    while (
      suffix < before.length - start &&
      suffix < after.length - start &&
      before[before.length - 1 - suffix] === after[after.length - 1 - suffix]
    )
      suffix++;
    const end = before.length - suffix,
      shift = after.length - before.length;
    return current
      .flatMap((mention) =>
        mention.end <= start
          ? [mention]
          : mention.start >= end
            ? [{ ...mention, start: mention.start + shift, end: mention.end + shift }]
            : [],
      )
      .filter(
        (mention) =>
          after.slice(mention.start, mention.end).join('') ===
          data.mentions.find((person) => person.id === mention.user_id)?.mention,
      );
  }
  function changed(value: string, caret: number) {
    setText(value);
    setMentions((current) => moveMentions(text, value, current));
    const match = value.slice(0, caret).match(/(?:^|\s)@([^@\n]{0,60})$/);
    setQuery(match ? { start: caret - match[1].length - 1, end: caret, value: match[1] } : null);
    setActive(0);
  }
  function choose(index: number) {
    const person = suggestions[index];
    if (!person || !query) return;
    const value = text.slice(0, query.start) + person.mention + ' ' + text.slice(query.end),
      start = Array.from(text.slice(0, query.start)).length,
      end = start + Array.from(person.mention).length;
    setText(value);
    setMentions((current) => [
      ...moveMentions(text, value, current),
      { user_id: person.id, start, end },
    ]);
    setQuery(null);
    requestAnimationFrame(() => {
      input.current?.focus();
      input.current?.setSelectionRange(
        query.start + person.mention.length + 1,
        query.start + person.mention.length + 1,
      );
    });
  }
  function add(selected: File[]) {
    if (pending) return;
    setError('');
    if (files.length + selected.length > data.attachment_limit) {
      setError(`Możesz dodać maksymalnie ${data.attachment_limit} plików.`);
      return;
    }
    if (selected.some((file) => file.size > data.attachment_max_size)) {
      setError('Jeden z plików przekracza dopuszczalny rozmiar.');
      return;
    }
    setFiles((current) => [...current, ...selected]);
  }
  async function submit() {
    if (pending) return;
    const form = new FormData();
    form.set('action', 'comment');
    form.set('message', text);
    form.set('activity_mentions', JSON.stringify(mentions));
    files.forEach((file) => form.append('comment_attachments', file));
    const ok = await send(form);
    if (ok && life.current) {
      setText('');
      setFiles([]);
      setMentions([]);
      setQuery(null);
    }
  }
  function paste(event: ClipboardEvent) {
    const images = [...event.clipboardData.files];
    if (images.length) {
      event.preventDefault();
      add(images);
    }
  }
  function drop(event: DragEvent) {
    if (!event.dataTransfer.files.length) return;
    event.preventDefault();
    add([...event.dataTransfer.files]);
  }
  return (
    <div
      className="tasks-issue-comment tasks-issue-comment--mentions"
      onDragOver={(event) => {
        if (event.dataTransfer.types.includes('Files')) event.preventDefault();
      }}
      onDrop={drop}
    >
      <div className="tasks-mention-composer">
        <textarea
          ref={input}
          aria-label="Treść komentarza"
          aria-autocomplete="list"
          aria-expanded={!!suggestions.length}
          aria-controls="react-mention-suggestions"
          aria-activedescendant={suggestions.length ? `react-mention-${active}` : undefined}
          className="tasks-issue-comment-input"
          rows={3}
          placeholder="Napisz komentarz; wpisz @ i imię osoby..."
          value={text}
          onChange={(event) => changed(event.target.value, event.target.selectionStart)}
          onPaste={paste}
          disabled={pending}
          onKeyDown={(event) => {
            if (
              suggestions.length &&
              ['ArrowUp', 'ArrowDown', 'Enter', 'Escape'].includes(event.key)
            ) {
              event.preventDefault();
              if (event.key === 'Escape') setQuery(null);
              else if (event.key === 'Enter') choose(active);
              else
                setActive(
                  (active + (event.key === 'ArrowDown' ? 1 : -1) + suggestions.length) %
                    suggestions.length,
                );
            } else if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
              event.preventDefault();
              void submit();
            }
          }}
        />
        {suggestions.length ? (
          <div
            id="react-mention-suggestions"
            className="tasks-filter-menu tasks-mention-menu"
            role="listbox"
            aria-label="Osoby z Workspace"
          >
            {suggestions.map((person, index) => (
              <button
                id={`react-mention-${index}`}
                type="button"
                role="option"
                aria-selected={active === index}
                key={person.id}
                className="tasks-project-menu-button"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(index)}
              >
                <span>{person.label}</span>
                <small>{person.email}</small>
              </button>
            ))}
          </div>
        ) : null}
      </div>
      {files.length ? (
        <div
          className="tasks-comment-images tasks-comment-images--pending"
          aria-label="Pliki do wysłania"
        >
          {files.map((file, index) => (
            <span className="tasks-comment-file" key={index}>
              {file.name}
              <button
                type="button"
                className="tasks-issue-tool"
                aria-label={`Usuń plik ${file.name} z komentarza`}
                disabled={pending}
                onClick={() =>
                  setFiles((current) => current.filter((_, position) => position !== index))
                }
              >
                <Icon name="x" />
              </button>
            </span>
          ))}
        </div>
      ) : null}
      {error ? (
        <p className="tasks-comment-error" role="alert">
          {error}
        </p>
      ) : null}
      <div className="tasks-issue-comment-tools">
        <input
          ref={picker}
          type="file"
          accept={data.attachment_accept}
          multiple
          hidden
          disabled={pending}
          onChange={(event) => {
            add([...(event.target.files || [])]);
            event.target.value = '';
          }}
        />
        <button
          type="button"
          className="tasks-issue-tool tasks-issue-tool--labelled tasks-comment-add"
          disabled={pending}
          onClick={() => picker.current?.click()}
        >
          <Icon name="paperclip" />
          <span>Dodaj pliki</span>
        </button>
        <span className="u-sr-only">
          Możesz też wkleić zdjęcie ze schowka lub przeciągnąć pliki do pola komentarza. Maksymalnie{' '}
          {data.attachment_limit} plików.
        </span>
        <button
          type="button"
          className="tasks-issue-send"
          aria-label="Wyślij komentarz"
          disabled={pending}
          onClick={() => void submit()}
        >
          <Icon name="send" />
        </button>
      </div>
    </div>
  );
}
