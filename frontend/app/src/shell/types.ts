import type { AvatarData } from '../shared/Avatar';
import type { ShellData, ToastMessage } from './navigation-types';
export interface PanelsConfig {
  shell: ShellData;
  messages: ToastMessage[];
  user_id: string;
  api_url: string;
  search_url: string;
  notifications_url: string;
  action_url: string;
  pending_invitation_count: number;
}
export interface Summary {
  unread_count: number;
  pending_invitation_count: number;
  revision: (number | null)[];
}
export interface SearchPayload {
  query: string;
  recent?: boolean;
  total: number;
  truncated?: boolean;
  groups: {
    key: string;
    label: string;
    icon: string;
    has_more: boolean;
    results: {
      title: string;
      type: string;
      url: string;
      icon: string;
      meta: string;
      eyebrow: string;
      new_tab?: boolean;
    }[];
  }[];
}
export interface NotificationItem {
  key: string;
  title: string;
  url: string;
  actor_label: string;
  actor_avatar: AvatarData;
  action_message: string;
  workplace_label: string;
  source_label: string;
  object_id: string | number;
  location_label: string;
  group_label: string;
  event_label: string;
  full_date: string;
  action_label: string;
  is_read: boolean;
  is_archived: boolean;
  is_invitation: boolean;
  created_at: string;
  time: string;
  details: { label: string; from_label: string; text: string }[];
}
export interface Inbox extends Summary {
  items: NotificationItem[];
  count: number;
  total: number;
  filtered_unread_count: number;
  deletable_count: number;
  snapshot: string;
  next_cursor: string;
  filters: { view: string; workspace: string };
  workplaces: { id: string; name: string; avatar: AvatarData }[];
}
