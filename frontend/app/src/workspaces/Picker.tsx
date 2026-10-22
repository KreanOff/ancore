import { useEffect, useId, useRef, useState } from 'react';
import { Avatar, type AvatarData } from '../shared/Avatar';
import { pageRequest } from '../shared/page';
interface Candidate {
  name: string;
  email: string;
  avatar: AvatarData;
}
export function PersonIdentity({ person }: { person: Candidate }) {
  return (
    <span className="tasks-responsible-select__person">
      <Avatar data={person.avatar} className="tasks-directory-avatar" />
      <span className="tasks-responsible-select__identity">
        <span className="workplace-team__name" title={person.name}>
          {person.name}
        </span>
        <span className="workplace-team__name" title={person.email}>
          {person.email}
        </span>
      </span>
    </span>
  );
}
export default function Picker({
  api,
  url,
  token,
  value,
  onChange,
  sharing = false,
}: {
  api: string;
  url: string;
  token: string;
  value: string;
  onChange: (value: string) => void;
  sharing?: boolean;
}) {
  const [people, setPeople] = useState<Candidate[]>([]),
    [selected, setSelected] = useState<Candidate | null>(null),
    [status, setStatus] = useState('Wpisz co najmniej 2 znaki, aby wyszukać osobę.'),
    [index, setIndex] = useState(-1),
    [open, setOpen] = useState(false);
  const id = useId(),
    version = useRef(0),
    request = useRef<AbortController>(),
    timer = useRef<ReturnType<typeof setTimeout>>(),
    host = useRef<HTMLDivElement>(null),
    input = useRef<HTMLInputElement>(null),
    wanted = useRef(value);
  function close() {
    version.current++;
    clearTimeout(timer.current);
    request.current?.abort();
    setOpen(false);
    setIndex(-1);
    setStatus((current) => (current === 'Szukam osób…' ? '' : current));
  }
  function choose(person: Candidate) {
    close();
    wanted.current = person.email;
    onChange(person.email);
    setSelected(person);
    setStatus((sharing ? 'Udostępniasz: ' : 'Zapraszasz: ') + person.name + '.');
    input.current?.focus();
  }
  function search(text: string) {
    close();
    wanted.current = text;
    onChange(text);
    setSelected(null);
    setPeople([]);
    if (text.trim().length < 2) {
      setStatus('Wpisz co najmniej 2 znaki, aby wyszukać osobę.');
      return;
    }
    setStatus('Szukam osób…');
    const current = version.current;
    timer.current = setTimeout(async () => {
      const controller = new AbortController();
      request.current = controller;
      try {
        const result = await pageRequest<{ results: Candidate[]; has_more: boolean }>(
          api,
          url + '?q=' + encodeURIComponent(text.trim()),
          token,
          controller.signal,
        );
        if (current !== version.current || wanted.current !== text) return;
        const exact = result.results.find(
          (p) => p.email.toLocaleLowerCase() === text.trim().toLocaleLowerCase(),
        );
        if (exact) {
          choose(exact);
          return;
        }
        setPeople(result.results);
        setOpen(!!result.results.length);
        setStatus(
          !result.results.length
            ? sharing
              ? 'Brak pasujących osób. Wybierz członka Workspace, który nie ma jeszcze dostępu.'
              : 'Nie znaleziono osoby, którą można zaprosić. Sprawdź dane; członkowie i osoby z oczekującym zaproszeniem nie pojawiają się na liście.'
            : result.has_more
              ? 'Pokazano 10 osób. Doprecyzuj wyszukiwanie lub wybierz osobę.'
              : 'Wybierz osobę z listy.',
        );
      } catch {
        if (!controller.signal.aborted && current === version.current)
          setStatus(
            'Nie udało się pobrać podpowiedzi. Wpisz adres e-mail lub zmień tekst, aby spróbować ponownie.',
          );
      }
    }, 250);
  }
  useEffect(() => {
    const outside = (e: MouseEvent) => {
      if (!host.current?.contains(e.target as Node)) close();
    };
    document.addEventListener('click', outside);
    return () => {
      version.current++;
      clearTimeout(timer.current);
      request.current?.abort();
      document.removeEventListener('click', outside);
    };
  }, []);
  return (
    <div ref={host} data-team-invite-picker>
      <input
        ref={input}
        id={id + '-input'}
        name="email"
        className="form-input"
        autoComplete="off"
        spellCheck={false}
        placeholder="Wpisz imię, nazwisko, ID Ancore lub e-mail"
        aria-label="Osoba lub adres e-mail konta Ancore"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={open}
        aria-busy={status === 'Szukam osób…'}
        aria-controls={id + '-results'}
        aria-describedby={id + '-status'}
        aria-activedescendant={open && index >= 0 ? id + '-' + index : undefined}
        value={value}
        required
        onChange={(e) => search(e.target.value)}
        onFocus={() => {
          if (value.trim() && value !== selected?.email) search(value);
        }}
        onBlur={() => {
          clearTimeout(timer.current);
          request.current?.abort();
          version.current++;
        }}
        onKeyDown={(e) => {
          if (e.nativeEvent.isComposing) return;
          if (e.key === 'Escape' && (open || status === 'Szukam osób…')) {
            e.preventDefault();
            e.stopPropagation();
            close();
            setStatus('');
          } else if (e.key === 'Tab') close();
          else if (open && ['ArrowDown', 'ArrowUp', 'Enter'].includes(e.key)) {
            e.preventDefault();
            e.stopPropagation();
            if (e.key === 'Enter') choose(people[Math.max(0, index)]);
            else {
              const next =
                index < 0
                  ? e.key === 'ArrowDown'
                    ? 0
                    : people.length - 1
                  : (index + (e.key === 'ArrowDown' ? 1 : -1) + people.length) % people.length;
              setIndex(next);
              document.getElementById(id + '-' + next)?.scrollIntoView({ block: 'nearest' });
            }
          }
        }}
      />
      <p id={id + '-status'} className="workplace-invite__status" role="status" aria-live="polite">
        {status}
      </p>
      <div
        id={id + '-results'}
        className="workplace-invite__results"
        role="listbox"
        aria-label={sharing ? 'Osoby, którym możesz udostępnić' : 'Osoby, które możesz zaprosić'}
        hidden={!open}
      >
        {people.map((person, i) => (
          <button
            key={person.email}
            type="button"
            tabIndex={-1}
            id={id + '-' + i}
            role="option"
            aria-selected={index === i}
            className="tasks-project-menu-button"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => choose(person)}
          >
            <PersonIdentity person={person} />
          </button>
        ))}
      </div>
      {selected ? (
        <div className="workplace-invite__selected">
          <PersonIdentity person={selected} />
        </div>
      ) : null}
    </div>
  );
}
