import type { AvatarData } from '../shared/Avatar';
import type { FormSchema } from '../forms/FormDialog';
import type { Item, Status } from '../spaces/types';
export interface FileData {
  id: number;
  name: string;
  size: string;
  type_class: string;
  image: boolean;
  url: string;
}
export interface Activity {
  id: number;
  kind: string;
  action: string;
  message: string;
  created_at: string;
  actor: string;
  avatar: AvatarData;
  files: FileData[];
  metadata: {
    changes?: { field: string; from_label: string; to_label: string }[];
    from_label?: string;
    to_label?: string;
    old_status_label?: string;
    new_status_label?: string;
    fields?: string[];
    title?: string;
    count?: number;
    subtask_title?: string;
  };
}
export interface Log {
  id: number;
  author: string;
  avatar: AvatarData;
  duration_minutes: number;
  started_at: string;
  ended_at: string;
  description: string;
  form_values: Record<string, string | number>;
}
export interface Member {
  id: number | string;
  user_id: number;
  name: string;
  email: string;
  avatar: AvatarData;
  role: string;
  role_label: string;
  created_at: string | null;
  can_change: boolean;
}
export interface Team {
  can_manage: boolean;
  is_owner: boolean;
  share_form: FormSchema;
  members: Member[];
}
export interface TaskData {
  item: Item;
  space: { id: number; name: string; template: string; url: string };
  form: FormSchema;
  error: string;
  can_edit: boolean;
  can_manage: boolean;
  favorite: boolean;
  back_url: string;
  tabs: { key: string; label: string; icon: string; url: string }[];
  tab: string;
  edit_url: string;
  member_url: string;
  team_url: string;
  status: string;
  statuses: Status[];
  created_at: string;
  completion_date: string | null;
  created_by: { name: string; avatar: AvatarData } | null;
  visibility: string;
  comments: Activity[];
  history: Activity[];
  files: FileData[];
  children: Item[];
  log_form: FormSchema;
  subtask_form: FormSchema;
  work_log: {
    total_minutes: number;
    total_label: string;
    count: number;
    page: number;
    pages: number;
    previous: string;
    next: string;
    results: Log[];
  };
  team: Team;
  mentions: { id: number; username: string; email: string; mention: string; label: string }[];
  attachment_accept: string;
  attachment_limit: number;
  attachment_max_size: number;
  comment_draft: string;
}
