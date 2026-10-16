export async function documentRequest<T>(
  url: string,
  token: string,
  signal: AbortSignal,
  body?: FormData,
  headers: Record<string, string> = {},
): Promise<T> {
  const target = new URL(url, location.origin);
  if (target.origin !== location.origin) throw new Error('Nieprawidłowy adres żądania.');
  const response = await fetch(target, {
    method: body ? 'POST' : 'GET',
    body,
    credentials: 'same-origin',
    redirect: 'error',
    cache: 'no-store',
    headers: { Accept: 'application/json', 'X-CSRFToken': token, ...headers },
    signal: AbortSignal.any([signal, AbortSignal.timeout(20000)]),
  });
  if (!response.headers.get('Content-Type')?.includes('application/json'))
    throw new Error('Nieprawidłowa odpowiedź serwera. Sprawdź sesję i odśwież stronę.');
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Nie udało się zapisać. Spróbuj ponownie.');
  return result;
}
