export interface Page {
  type: string;
  title: string;
  url: string;
  api_url: string;
  data: unknown;
  styles?: string[];
}
export interface PageProps {
  initial: Page;
  csrfToken: string;
}
export function setPageLocation(url: string | URL, push = false) {
  if (window.AncoreApp?.setLocation) window.AncoreApp.setLocation(String(url), push);
  else history[push ? 'pushState' : 'replaceState'](history.state, '', url);
}
export class PageError extends Error {
  constructor(
    public status: number,
    public data: Record<string, unknown>,
  ) {
    const details =
      data.data && typeof data.data === 'object'
        ? (data.data as Record<string, unknown>)
        : undefined;
    super(
      String(
        data.message ||
          data.error ||
          details?.error ||
          'Nie udało się wykonać operacji. Spróbuj ponownie.',
      ),
    );
  }
}
export async function pageRequest<T>(
  api: string,
  target: string,
  token: string,
  signal: AbortSignal,
  body?: FormData | Record<string, unknown>,
): Promise<T> {
  const url = new URL(target, location.origin);
  if (url.origin !== location.origin) throw new Error('Nieprawidłowy adres żądania.');
  const response = await fetch(`${api}?url=${encodeURIComponent(url.pathname + url.search)}`, {
    method: body ? 'POST' : 'GET',
    body: body && !(body instanceof FormData) ? JSON.stringify(body) : body,
    credentials: 'same-origin',
    redirect: 'error',
    signal: AbortSignal.any([signal, AbortSignal.timeout(20000)]),
    headers: {
      Accept: 'application/json',
      'X-CSRFToken': token,
      ...(body && !(body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
    },
  });
  if (!response.headers.get('content-type')?.includes('application/json'))
    throw new Error('Nieprawidłowa odpowiedź serwera. Odśwież stronę.');
  const result = await response.json();
  if (!response.ok) throw new PageError(response.status, result);
  return result as T;
}
export function navigate(url: string) {
  const app = window.AncoreApp;
  if (app && (!app.canNavigatePartially || app.canNavigatePartially(url))) return app.navigate(url);
  location.href = url;
}
