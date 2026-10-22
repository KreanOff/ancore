import type { AvatarData } from '../shared/Avatar';
import type { EmojiArt } from '../shared/Emoji';
import type { Page } from '../shared/page';
export interface Link {
  key: string;
  label: string;
  icon: string;
  url: string;
  is_active: boolean;
}
export interface CollectionRow {
  id: string;
  name: string;
  url: string;
  avatar?: AvatarData;
  icon?: string;
  emoji?: string;
  emoji_art?: EmojiArt;
  active: boolean;
  favorite: boolean;
  favorite_url: string;
  settings_url?: string;
  members_url?: string;
  description?: string;
  detail?: string;
  actions?: { label: string; icon: string; url: string }[];
}
export interface Collection {
  key: string;
  label: string;
  icon: string;
  url: string;
  directory_url: string;
  search_url: string;
  create_url: string;
  task_search_url?: string;
  manage_url: string;
  starred: CollectionRow[];
  recent: CollectionRow[];
}
export interface ShellData {
  account_id: string;
  workplace_id: string;
  mode: string;
  url: string;
  navigation_url: string;
  refresh_url: string;
  build_id: string;
  workplaces: { id: string; name: string; avatar: AvatarData; switch_url: string }[];
  profile: { name: string; avatar: AvatarData; url: string; active: boolean };
  settings_url: string;
  settings_active: boolean;
  workplaces_url: string;
  links: Record<string, Link>;
  favorites: Link[];
  favorite_toggle_url: string;
  favorite_reorder_url: string;
  collections: Collection[];
  default_pulpit_url: string;
  default_pulpit_icon?: string;
  default_pulpit_emoji?: string;
  default_pulpit_emoji_art?: EmojiArt;
  default_pulpit_active: boolean;
  filter_search_active: boolean;
  editor: {
    title: string;
    return_url: string;
    links: { key: string; label: string; icon: string; url: string; active: boolean }[];
  };
}
export interface ToastMessage {
  message: string;
  type: string;
}
export interface NavigationEnvelope {
  page: Page;
  shell: ShellData;
  csrf_token: string;
  messages: ToastMessage[];
}
export interface Position {
  window: { top: number; left: number };
  elements: { selector: string; positions: { top: number; left: number }[] }[];
}
export interface ReturnContext {
  mode: string;
  url: string;
  label: string;
  position?: Position;
  accountId: string;
  workplaceId: string;
  previousManagementReturn?: ReturnContext | null;
}
export interface NavigateOptions {
  replace?: boolean;
  updateHistory?: boolean;
  restorePosition?: Position;
  managementReturnNavigation?: boolean;
  previousManagementReturn?: ReturnContext | null;
  managementReturnFallback?: string;
}
