export class ApiError extends Error {
  constructor(
    public status: number,
    public data: Record<string, unknown>,
  ) {
    super(
      typeof data.message === 'string'
        ? data.message
        : 'Nie udało się wykonać operacji. Spróbuj ponownie.',
    );
  }
}

export async function request<T>(
  url: string,
  csrfToken: string,
  signal: AbortSignal,
  options: RequestInit = {},
): Promise<T> {
  const target = new URL(url, window.location.origin);
  if (target.origin !== window.location.origin) throw new Error('Nieprawidłowy adres API.');
  const response = await fetch(target, {
    ...options,
    credentials: 'same-origin',
    redirect: 'error',
    signal: AbortSignal.any([signal, AbortSignal.timeout(15000)]),
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
      ...options.headers,
    },
  });
  if (!response.headers.get('content-type')?.includes('application/json'))
    throw new Error(
      'Nie udało się odczytać odpowiedzi serwera. Odśwież stronę i spróbuj ponownie.',
    );
  const data = await response.json();
  if (!response.ok) throw new ApiError(response.status, data);
  return data as T;
}

export function errorMessage(error: unknown): string {
  return error instanceof Error && !(error instanceof TypeError)
    ? error.message
    : 'Nie udało się połączyć z serwerem. Spróbuj ponownie.';
}
