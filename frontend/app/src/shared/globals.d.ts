export {};
declare global {
  interface Window {
    AncoreReactRuntime?: {
      dispose(): void;
      preparePage(data: import('../shell/navigation-types').NavigationEnvelope): Promise<void>;
      renderPage(data: import('../shell/navigation-types').NavigationEnvelope): void;
    };
    AncorePhotoEditors?: { init(root: Element): void };
    AncoreWorkplaceAvatars?: { init(root: Element): void; dispose(form: HTMLFormElement): void };
    AncoreApp?: {
      setLocation?(url: string, push?: boolean): void;
      canNavigatePartially?(url: string): boolean;
      invalidateManagementReturn?(paths: string[]): void;
      navigate(
        url: string,
        options?: import('../shell/navigation-types').NavigateOptions,
      ): Promise<boolean>;
    };
    AncoreIcons?: {
      create(name: string, options?: { className?: string }): HTMLElement;
      render(scope: Element): void;
    };
    AncoreCustomSelect?: { refresh(scope: Element): void; closeAll(): void };
    AncoreDropdownLayer?: {
      open(menu: HTMLElement, anchor: HTMLElement, onClose: () => void): void;
      hide(menu: HTMLElement): void;
      dismiss(restoreFocus?: boolean): void;
    };
    AncoreTaskModals?: {
      open(modal: HTMLElement, focus?: HTMLElement | null): void;
      close(modal: HTMLElement): void;
    };
    showNotification?: (
      message: string,
      type?: string,
      options?: { duration?: number; dedupeKey?: string },
    ) => HTMLElement | null;
    hideNotification?: (element: HTMLElement | null | undefined) => void;
    closeNotification?: (element: HTMLElement | null | undefined) => void;
    escapeHtmlForModal: (message: string) => string;
    showConfirmModal: (options: {
      title: string;
      message?: string;
      messageText?: string;
      confirmText: string;
      cancelText: string;
      confirmClass?: string;
      onConfirm: () => void;
    }) => void;
  }
}
