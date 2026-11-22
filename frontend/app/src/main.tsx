import { Component, type ComponentType, type ReactNode } from 'react';
import { flushSync } from 'react-dom';
import { createRoot, type Root } from 'react-dom/client';
import type { Page } from './shared/page';
import type { PageProps } from './shared/page';
import type { NavigationEnvelope } from './shell/navigation-types';

// A new hashed entry can arrive through partial navigation after a deployment.
// Dispose the previous module's roots and listeners before registering this one.
window.AncoreReactRuntime?.dispose();
let disposed = false;
const roots = new Map<HTMLElement, Root>();
const pending = new WeakSet<HTMLElement>();
let panelsRoot: Root | undefined;
let mountingPanels = false;
let PageComponent: ComponentType<PageProps>;
const stylesEnd = document.querySelector('meta[name="ancore-screen-styles"]');
const styles = new Map(
  Array.from(document.querySelectorAll<HTMLLinkElement>('link[data-screen-stylesheet]'), (link) => [
    link.href,
    { link, ready: Promise.resolve() },
  ]),
);

function screenStyle(href: string) {
  const url = new URL(href, location.origin).href;
  const existing = styles.get(url);
  if (existing) return existing;

  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = url;
  link.dataset.screenStylesheet = '';
  // Fetch now, but keep the current screen's cascade until navigation commits.
  link.media = 'not all';
  const ready = new Promise<void>((resolve, reject) => {
    const failed = () => {
      clearTimeout(timer);
      link.remove();
      styles.delete(url);
      reject(new Error('Nie udało się wczytać stylów ekranu.'));
    };
    const timer = setTimeout(failed, 15000);
    link.onload = () => {
      clearTimeout(timer);
      resolve();
    };
    link.onerror = failed;
    document.head.insertBefore(link, stylesEnd);
  });
  const entry = { link, ready };
  styles.set(url, entry);
  return entry;
}

function applyScreenStyles(urls: string[]) {
  const active = new Set(urls.map((href) => screenStyle(href).link));
  for (const { link } of styles.values()) {
    if (!active.has(link)) link.media = 'not all';
  }
  let before = stylesEnd;
  for (const link of [...active].reverse()) {
    if (link.nextElementSibling !== before) document.head.insertBefore(link, before);
    link.removeAttribute('media');
    before = link;
  }
}

async function preparePage(envelope: NavigationEnvelope) {
  const loads = (envelope.page.styles || []).map((href) => screenStyle(href).ready);
  loads.push(
    import('./PageApp').then(async (module) => {
      PageComponent = module.default;
      await module.preloadPage(envelope.page.type);
    }),
  );
  await Promise.all(loads);
}
function renderPage(envelope: NavigationEnvelope) {
  unmount();
  applyScreenStyles(envelope.page.styles || []);
  document.querySelector('[data-right-sidebar-fallback]')?.remove();
  const container = document.querySelector<HTMLElement>('.main-content .page-container')!;
  container.className = 'page-container full-width';
  const host = document.createElement('div'),
    modals = document.createElement('div');
  host.dataset.reactRoot = 'page';
  host.dataset.csrfToken = envelope.csrf_token;
  host.style.display = 'contents';
  modals.id = 'app-page-modals';
  container.replaceChildren(host, modals);
  const root = createRoot(host);
  roots.set(host, root);
  document.body.classList.remove(
    'modal-open',
    'profile-edit-modal-open',
    'contacts-photo-editor-open',
    'is-resizing-directory-columns',
  );
  flushSync(() =>
    root.render(
      <FrontendBoundary>
        <PageComponent initial={envelope.page} csrfToken={envelope.csrf_token} />
      </FrontendBoundary>,
    ),
  );
  document.body.classList.toggle('tasks-ui', !!container.querySelector('.tasks-page'));
}
class FrontendBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <div className="tasks-empty-state" role="alert">
        <p>Nie udało się wyświetlić ekranu.</p>
        <button className="btn btn-secondary" onClick={() => window.location.reload()}>
          Odśwież stronę
        </button>
      </div>
    ) : (
      this.props.children
    );
  }
}

async function mount() {
  if (disposed) return;
  void mountPanels();
  const host = document.querySelector<HTMLElement>('[data-react-root="page"]');
  if (!host || roots.has(host) || pending.has(host)) return;
  pending.add(host);
  try {
    const data = document.getElementById(host.dataset.bootstrapId || '')?.textContent;
    if (!data) throw new Error('Missing frontend data');
    const initial: Page = JSON.parse(data);
    const PageApp = (await import('./PageApp')).default;
    if (disposed || !host.isConnected) return;
    document.getElementById('app-page-modals')?.replaceChildren();
    document.querySelector('[data-right-sidebar-fallback]')?.remove();
    const root = createRoot(host);
    roots.set(host, root);
    root.render(
      <FrontendBoundary>
        <PageApp initial={initial} csrfToken={host.dataset.csrfToken || ''} />
      </FrontendBoundary>,
    );
  } catch (error) {
    window.showNotification?.(
      'Nie udało się wczytać interfejsu aplikacji. Odśwież stronę.',
      'error',
    );
    console.error(error);
  } finally {
    pending.delete(host);
  }
}

async function mountPanels() {
  const host = document.querySelector<HTMLElement>('[data-react-global-panels]');
  if (!host || panelsRoot || mountingPanels || disposed) return;
  mountingPanels = true;
  try {
    const initial = JSON.parse(document.getElementById('ancore-global-panels-data')!.textContent!);
    const Panels = (await import('./shell/Shell')).default;
    if (disposed || !host.isConnected) return;
    ['app-notifications', 'app-sticker-host'].forEach((id) =>
      document.getElementById(id)?.replaceChildren(),
    );
    panelsRoot = createRoot(host);
    panelsRoot.render(
      <FrontendBoundary>
        <Panels config={initial} token={host.dataset.csrfToken || ''} />
      </FrontendBoundary>,
    );
  } catch (error) {
    console.error(error);
    window.showNotification?.('Nie udało się wczytać paneli aplikacji. Odśwież stronę.', 'error');
  } finally {
    mountingPanels = false;
  }
}

function unmount() {
  roots.forEach((root) => root.unmount());
  roots.clear();
}
window.AncoreReactRuntime = {
  preparePage,
  renderPage,
  dispose() {
    disposed = true;
    document.removeEventListener('ancore:content-unloading', unmount);
    document.removeEventListener('ancore:content-loaded', mount);
    document.removeEventListener('DOMContentLoaded', mount);
    unmount();
    panelsRoot?.unmount();
  },
};
document.addEventListener('ancore:content-unloading', unmount);
document.addEventListener('ancore:content-loaded', mount);
if (document.readyState === 'loading')
  document.addEventListener('DOMContentLoaded', mount, { once: true });
else void mount();
