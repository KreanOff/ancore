import { Component, type ComponentType, type ReactNode } from 'react';
import { flushSync } from 'react-dom';
import { createRoot, type Root } from 'react-dom/client';
import type { Directory } from './resources/types';
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
let ResourcesComponent: ComponentType<{ initial: Directory; csrfToken: string }>;
const styles = new Map<string, Promise<void>>();
async function preparePage(envelope: NavigationEnvelope) {
  const loads = (envelope.page.styles || []).map((href) => {
    const url = new URL(href, location.origin).href;
    if (styles.has(url)) return styles.get(url)!;
    if (
      [...document.querySelectorAll<HTMLLinkElement>('link[rel=stylesheet]')].some(
        (link) => link.href === url,
      )
    )
      return Promise.resolve();
    const pending = new Promise<void>((resolve, reject) => {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = url;
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
      document.head.append(link);
    });
    styles.set(url, pending);
    return pending;
  });
  if (envelope.page.type === 'resources') {
    loads.push(
      import('./resources/App').then((module) => {
        ResourcesComponent = module.default;
      }),
    );
  } else {
    loads.push(
      import('./PageApp').then(async (module) => {
        PageComponent = module.default;
        await module.preloadPage(envelope.page.type);
      }),
    );
  }
  await Promise.all(loads);
}
function renderPage(envelope: NavigationEnvelope) {
  unmount();
  document.querySelector('[data-right-sidebar-fallback]')?.remove();
  const container = document.querySelector<HTMLElement>('.main-content .page-container')!;
  container.className = 'page-container full-width';
  const host = document.createElement('div'),
    modals = document.createElement('div');
  host.dataset.reactRoot = envelope.page.type === 'resources' ? 'resources' : 'page';
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
        {envelope.page.type === 'resources' ? (
          <ResourcesComponent
            initial={envelope.page.data as Directory}
            csrfToken={envelope.csrf_token}
          />
        ) : (
          <PageComponent initial={envelope.page} csrfToken={envelope.csrf_token} />
        )}
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
  const host = document.querySelector<HTMLElement>('[data-react-root]');
  if (!host || roots.has(host) || pending.has(host)) return;
  pending.add(host);
  try {
    const data = document.getElementById(host.dataset.bootstrapId || '')?.textContent;
    if (!data) throw new Error('Missing frontend data');
    const initial = JSON.parse(data);
    let content: ReactNode;
    if (host.dataset.reactRoot === 'resources') {
      const ResourcesApp = (await import('./resources/App')).default;
      content = (
        <ResourcesApp initial={initial as Directory} csrfToken={host.dataset.csrfToken || ''} />
      );
    } else {
      const PageApp = (await import('./PageApp')).default;
      content = <PageApp initial={initial as Page} csrfToken={host.dataset.csrfToken || ''} />;
    }
    if (disposed || !host.isConnected) return;
    // Replace the server fallback modal with the React portal on direct editor URLs.
    document.querySelector('[data-resource-modal-host]')?.replaceChildren();
    if (host.dataset.reactRoot === 'page')
      document.getElementById('app-page-modals')?.replaceChildren();
    document.querySelector('[data-right-sidebar-fallback]')?.remove();
    const root = createRoot(host);
    roots.set(host, root);
    root.render(<FrontendBoundary>{content}</FrontendBoundary>);
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
