import { request, ApiError, errorMessage } from '../shared/api';
import { flushSync } from 'react-dom';
import type {
  NavigationEnvelope,
  NavigateOptions,
  ReturnContext,
  Position,
  ShellData,
} from './navigation-types';

const managementModes = new Set(['workplaces', 'pulpit-editor']);
const scrollSelectors = [
  '.main-content',
  '.settings-scroll-area',
  '.work-content',
  '.tasks-table-wrap',
  '.tasks-board',
];
export function capturePosition(): Position {
  return {
    window: { top: scrollY, left: scrollX },
    elements: scrollSelectors.map((selector) => ({
      selector,
      positions: [...document.querySelectorAll(selector)].map((e) => ({
        top: e.scrollTop,
        left: e.scrollLeft,
      })),
    })),
  };
}
function restorePosition(position?: Position) {
  window.scrollTo(position?.window || { top: 0, left: 0 });
  for (const entry of position?.elements || [])
    if (scrollSelectors.includes(entry.selector))
      document.querySelectorAll(entry.selector).forEach((e, i) => {
        if (entry.positions[i]) e.scrollTo(entry.positions[i]);
      });
}
function urlFor(href: string) {
  try {
    return new URL(href, location.href);
  } catch {
    return null;
  }
}
export function canNavigate(href: string) {
  if (document.querySelector('[data-app-full-navigation]')) return false;
  const url = urlFor(href);
  if (!url || url.origin !== location.origin) return false;
  const path = url.pathname.replace(
    /^\/workplaces\/[^/]+\/(?=(spaces|space|teams|filters|dashboards|resources|for-you|calendar|documents|office)(\/|$))/,
    '/',
  );
  return [
    /^\/$/,
    /^\/settings\/?$/,
    /^\/accounts\/profile\/?$/,
    /^\/workplaces\/?$/,
    /^\/(calendar|for-you|documents|office)\/?$/,
    /^\/resources\/(?:create\/|\d+\/(?:edit\/)?)?$/,
    /^\/spaces\/(?:create\/|manage\/(?:create\/|\d+\/edit\/)?)?$/,
    /^\/space\/[-a-zA-Z0-9_]+\/(?:configuration\/|tasks\/[^/]+\/)?$/,
    /^\/teams\/(?:\d+\/)?$/,
    /^\/filters\/(?:search\/|new\/|\d+\/(?:edit\/)?|manage\/(?:new\/|\d+\/edit\/)?)?$/,
    /^\/dashboards\/(?:[-a-zA-Z0-9_]+\/)?(?:create\/|edit\/|access\/|gadgets\/(?:add\/|\d+\/edit\/)?)?$/,
    /^\/dashboards\/manage\/(?:create\/|[-a-zA-Z0-9_]+\/(?:(?:edit|access)\/|gadgets\/(?:add\/|\d+\/edit\/)?))?$/,
  ].some((pattern) => pattern.test(path));
}
function modeFor(href: string) {
  const url = urlFor(href);
  if (!url || url.origin !== location.origin) return '';
  if (/^\/workplaces\/?$/.test(url.pathname)) return 'workplaces';
  const path = url.pathname.replace(/^\/workplaces\/[^/]+\/(?=(spaces|dashboards|filters)\/)/, '/');
  if (/^\/dashboards\/(manage\/)?[-a-zA-Z0-9_]+\/(edit|access|gadgets)(\/|$)/.test(path))
    return 'pulpit-editor';
  return '';
}
export function startNavigation(
  initial: ShellData,
  token: string,
  apply: (shell: ShellData, context: ReturnContext | null) => void,
) {
  const lifetime = new AbortController();
  let active: AbortController | undefined;
  let data = initial,
    renderedUrl = location.href,
    index = history.state?.ancoreNavigationIndex || 0;
  let attempt = 0,
    restoringHistory = false;
  const invalidated = new Set<string>();
  const key = (mode: string) =>
    `ancoreManagementReturn:${data.account_id}:${data.workplace_id}:${mode}`;
  function valid(value: ReturnContext | null, mode: string, depth = 0): ReturnContext | null {
    if (
      !value ||
      depth > 8 ||
      value.mode !== mode ||
      value.accountId !== data.account_id ||
      value.workplaceId !== data.workplace_id ||
      typeof value.url !== 'string' ||
      typeof value.label !== 'string' ||
      !canNavigate(value.url) ||
      modeFor(value.url) === mode
    )
      return null;
    const path = urlFor(value.url)!.pathname;
    if ([...invalidated].some((prefix) => path.startsWith(prefix))) return null;
    return {
      ...value,
      previousManagementReturn: valid(
        value.previousManagementReturn || null,
        value.previousManagementReturn?.mode || '',
        depth + 1,
      ),
    };
  }
  function stored(mode: string) {
    try {
      return valid(JSON.parse(sessionStorage.getItem(key(mode)) || 'null'), mode);
    } catch {
      return null;
    }
  }
  function save(mode: string, value: ReturnContext | null) {
    if (managementModes.has(mode))
      try {
        if (value) sessionStorage.setItem(key(mode), JSON.stringify(value));
        else sessionStorage.removeItem(key(mode));
      } catch {
        /* History remains available. */
      }
  }
  function initialReturn() {
    if (!managementModes.has(data.mode)) return null;
    if (Object.hasOwn(history.state || {}, 'ancoreManagementReturn'))
      return valid(history.state.ancoreManagementReturn, data.mode);
    const type = (
      performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined
    )?.type;
    const referrerMode = modeFor(document.referrer);
    if (!['reload', 'back_forward'].includes(type || '') && referrerMode !== data.mode) {
      const child = stored(referrerMode);
      return child && urlFor(child.url)?.pathname === location.pathname
        ? valid(child.previousManagementReturn || null, data.mode)
        : null;
    }
    return stored(data.mode);
  }
  let returnContext = initialReturn();
  apply(data, returnContext);
  save(data.mode, returnContext);
  history.replaceState(
    {
      ...history.state,
      ancorePartialNavigation: true,
      ancoreNavigationIndex: index,
      ancoreManagementReturn: returnContext,
    },
    '',
    location.href,
  );

  let loadingTimer: ReturnType<typeof setTimeout> | undefined;
  let loadingPage: HTMLElement | null = null,
    wasInert = false;
  function loading(on: boolean) {
    clearTimeout(loadingTimer);
    document.body.classList.toggle('app-partial-navigation', on);
    const content = document.querySelector('.main-content');
    if (on) {
      content?.setAttribute('aria-busy', 'true');
      loadingTimer = setTimeout(() => {
        loadingPage = document.querySelector('.page-container');
        wasInert = Boolean(loadingPage?.inert);
        if (loadingPage) loadingPage.inert = true;
        const skeleton = document.getElementById('app-content-loading');
        if (skeleton) skeleton.hidden = false;
      }, 180);
    } else {
      content?.removeAttribute('aria-busy');
      const skeleton = document.getElementById('app-content-loading');
      if (skeleton) skeleton.hidden = true;
      if (loadingPage?.isConnected) loadingPage.inert = wasInert;
      loadingPage = null;
    }
  }
  async function navigate(href: string, options: NavigateOptions = {}): Promise<boolean> {
    let url = urlFor(href);
    if (!url || !canNavigate(url.href)) return false;
    const version = ++attempt,
      guards: Promise<unknown>[] = [];
    const leaving = new CustomEvent('ancore:before-navigate', {
      cancelable: true,
      detail: {
        url: url.href,
        waitUntil: (value: Promise<unknown>) => guards.push(Promise.resolve(value)),
      },
    });
    if (!document.dispatchEvent(leaving)) return false;
    if (guards.length) {
      const outcomes = await Promise.allSettled(guards);
      if (version !== attempt || outcomes.some((o) => o.status === 'rejected' || o.value === false))
        return false;
    }
    const source = {
      url: renderedUrl,
      mode: data.mode,
      context: returnContext,
      position: capturePosition(),
    };
    active?.abort();
    active = new AbortController();
    const controller = active;
    loading(true);
    try {
      let envelope: NavigationEnvelope | undefined;
      for (let redirects = 0; redirects < 6; redirects++) {
        const workspace = /^\/workplaces\/([^/]+)\//.exec(url.pathname)?.[1];
        const current = /^\/workplaces\/([^/]+)\//.exec(
          new URL(data.navigation_url, location.origin).pathname,
        )?.[1];
        if (workspace && workspace !== current) {
          location.assign(url.href);
          return true;
        }
        const response = await request<NavigationEnvelope & { redirect?: string }>(
          `${data.navigation_url}?url=${encodeURIComponent(url.pathname + url.search)}`,
          token,
          controller.signal,
        );
        if (response.redirect) {
          const next = urlFor(response.redirect);
          if (!next || next.origin !== location.origin)
            throw new Error('Nieprawidłowe przekierowanie.');
          if (!canNavigate(next.href)) {
            location.assign(next.href);
            return true;
          }
          url = next;
          continue;
        }
        envelope = response;
        break;
      }
      if (!envelope?.page || !envelope.shell) throw new Error('Nie udało się wczytać ekranu.');
      if (controller.signal.aborted || version !== attempt) return true;
      if (
        envelope.shell.account_id !== data.account_id ||
        envelope.shell.workplace_id !== data.workplace_id ||
        envelope.shell.build_id !== data.build_id
      ) {
        location.assign(url.href);
        return true;
      }
      let nextReturn: ReturnContext | null = null;
      const mode = envelope.shell.mode;
      if (managementModes.has(mode)) {
        if (options.updateHistory === false)
          nextReturn = valid(history.state?.ancoreManagementReturn, mode);
        else if (options.managementReturnNavigation)
          nextReturn = valid(options.previousManagementReturn || null, mode);
        else if (source.mode === mode) nextReturn = valid(source.context, mode);
        else {
          const sourcePath = urlFor(source.url)!.pathname;
          const label =
            source.mode === 'settings'
              ? 'Wróć do ustawień'
              : /\/dashboards(\/|$)/.test(sourcePath)
                ? 'Wróć do pulpitów'
                : /\/spaces?(\/|$)/.test(sourcePath)
                  ? 'Wróć do przestrzeni'
                  : sourcePath === '/'
                    ? 'Wróć do Workspace'
                    : 'Wróć do poprzedniego widoku';
          nextReturn = valid(
            {
              mode,
              url: source.url,
              label,
              position: source.position,
              previousManagementReturn: source.context,
              accountId: data.account_id,
              workplaceId: data.workplace_id,
            },
            mode,
          );
        }
      }
      // Load the route chunk and styles before removing the current screen.
      await window.AncoreReactRuntime!.preparePage(envelope);
      if (controller.signal.aborted || version !== attempt) return true;
      const destination = url.href;
      if (options.updateHistory !== false) {
        history.replaceState(
          { ...history.state, ancorePosition: source.position },
          '',
          location.href,
        );
        const replace = options.replace || destination === location.href;
        if (!replace) index++;
        history[replace ? 'replaceState' : 'pushState'](
          {
            ancorePartialNavigation: true,
            ancoreNavigationIndex: index,
            ancoreManagementReturn: nextReturn,
          },
          '',
          destination,
        );
      }
      document.dispatchEvent(new CustomEvent('ancore:content-unloading'));
      data = envelope.shell;
      token = envelope.csrf_token;
      renderedUrl = destination;
      returnContext = nextReturn;
      save(mode, returnContext);
      flushSync(() => apply(data, returnContext));
      window.AncoreReactRuntime!.renderPage(envelope);
      document.title = `${envelope.page.title} | ancore`;
      document.dispatchEvent(new CustomEvent('ancore:messages', { detail: envelope.messages }));
      document.dispatchEvent(
        new CustomEvent('ancore:content-loaded', { detail: { url: destination } }),
      );
      loading(false);
      const position =
        options.restorePosition ||
        (options.updateHistory === false ? history.state?.ancorePosition : undefined);
      requestAnimationFrame(() => {
        if (version !== attempt) return;
        restorePosition(position);
        if (!position && url?.hash) {
          try {
            document
              .getElementById(decodeURIComponent(url.hash.slice(1)))
              ?.scrollIntoView({ block: 'start' });
          } catch {
            /* Invalid fragment. */
          }
        }
        const heading = document.querySelector<HTMLElement>('.main-content h1');
        if (
          heading &&
          (!document.activeElement ||
            document.activeElement === document.body ||
            !document.activeElement.isConnected)
        ) {
          heading.tabIndex = -1;
          heading.focus({ preventScroll: true });
        }
      });
      return true;
    } catch (error) {
      if (controller.signal.aborted || version !== attempt) return true;
      if (
        error instanceof ApiError &&
        error.status === 404 &&
        options.managementReturnFallback &&
        options.managementReturnFallback !== href
      ) {
        invalidate([url.pathname]);
        return navigate(options.managementReturnFallback, {
          ...options,
          managementReturnFallback: undefined,
          previousManagementReturn: null,
        });
      }
      if (error instanceof ApiError && error.status === 401) {
        location.assign(`/accounts/login/?next=${encodeURIComponent(url.pathname + url.search)}`);
        return true;
      }
      window.showNotification?.(errorMessage(error), 'error');
      return false;
    } finally {
      if (active === controller) {
        active = undefined;
        loading(false);
      }
    }
  }
  function invalidate(paths: string[]) {
    for (const path of paths) {
      const url = urlFor(path);
      if (url?.origin === location.origin && url.pathname !== '/' && url.pathname.endsWith('/'))
        invalidated.add(url.pathname);
    }
    returnContext = valid(returnContext, data.mode);
    for (const mode of managementModes) save(mode, stored(mode));
    history.replaceState(
      { ...history.state, ancoreManagementReturn: returnContext },
      '',
      location.href,
    );
    apply(data, returnContext);
  }
  window.AncoreApp = {
    setLocation(href, push = false) {
      const url = urlFor(href);
      if (!url || url.origin !== location.origin) return;
      if (push) {
        history.replaceState(
          { ...history.state, ancorePosition: capturePosition() },
          '',
          location.href,
        );
        index++;
      }
      history[push ? 'pushState' : 'replaceState'](
        { ...history.state, ancoreNavigationIndex: index },
        '',
        url.href,
      );
      renderedUrl = url.href;
    },
    canNavigatePartially: canNavigate,
    navigate,
    invalidateManagementReturn: invalidate,
  };
  const { signal } = lifetime;
  document.addEventListener(
    'click',
    (event) => {
      if (
        event.defaultPrevented ||
        event.button ||
        event.metaKey ||
        event.ctrlKey ||
        event.altKey ||
        event.shiftKey
      )
        return;
      const link = (event.target as Element).closest<HTMLAnchorElement>('a[href]');
      if (
        !link ||
        link.download ||
        link.hasAttribute('download') ||
        link.closest('[data-app-full-navigation]') ||
        (link.target && link.target !== '_self')
      )
        return;
      const url = urlFor(link.href);
      if (!url || !canNavigate(link.href)) return;
      if (url.pathname === location.pathname && url.search === location.search && url.hash) return;
      event.preventDefault();
      const back = link.dataset.managementReturn === data.mode;
      void navigate(
        link.href,
        back
          ? {
              managementReturnNavigation: true,
              previousManagementReturn: returnContext?.previousManagementReturn,
              restorePosition: returnContext?.position,
              managementReturnFallback: link.dataset.defaultReturnUrl,
            }
          : {},
      );
    },
    { signal },
  );
  document.addEventListener(
    'submit',
    (event) => {
      if (event.defaultPrevented || !(event.target instanceof HTMLFormElement)) return;
      const form = event.target,
        submit = event.submitter as HTMLButtonElement | null;
      if (
        (submit?.formMethod || form.method).toLowerCase() !== 'get' ||
        ((submit?.formTarget || form.target) && (submit?.formTarget || form.target) !== '_self')
      )
        return;
      const url = urlFor(submit?.getAttribute('formaction') || form.action);
      if (!url || !canNavigate(url.href)) return;
      event.preventDefault();
      url.search = new URLSearchParams(
        new FormData(form, submit) as unknown as Record<string, string>,
      ).toString();
      void navigate(url.href);
    },
    { signal },
  );
  window.addEventListener(
    'popstate',
    async (event) => {
      if (restoringHistory) {
        restoringHistory = false;
        return;
      }
      const old = urlFor(renderedUrl)!,
        next = urlFor(location.href)!;
      if (old.pathname === next.pathname && old.search === next.search && old.hash !== next.hash) {
        index = event.state?.ancoreNavigationIndex ?? index;
        renderedUrl = next.href;
        return;
      }
      if (!canNavigate(next.href)) {
        location.reload();
        return;
      }
      const previous = index;
      index = event.state?.ancoreNavigationIndex ?? index;
      if (!(await navigate(next.href, { updateHistory: false }))) {
        const delta = previous - index;
        index = previous;
        if (delta) {
          restoringHistory = true;
          history.go(delta);
        } else history.replaceState(history.state, '', renderedUrl);
      }
    },
    { signal },
  );
  const hideLoader = () => {
    document.documentElement.classList.remove('app-page-loading', 'app-shell-booting');
    document.body.classList.remove('app-page-loading');
    document.getElementById('app-loading-overlay')?.setAttribute('aria-hidden', 'true');
  };
  window.addEventListener('pageshow', hideLoader, { signal });
  window.addEventListener(
    'beforeunload',
    (event) => {
      setTimeout(() => {
        if (event.defaultPrevented) hideLoader();
      }, 0);
    },
    { signal },
  );
  hideLoader();
  return () => {
    lifetime.abort();
    active?.abort();
    loading(false);
    if (window.AncoreApp?.navigate === navigate) delete window.AncoreApp;
  };
}
