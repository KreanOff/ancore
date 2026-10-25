import type { AvatarData } from '../shared/Avatar';
import type { FormSchema } from '../forms/FormDialog';
export interface WorkspaceForm extends FormSchema {
  automatic_avatar: AvatarData;
}
export interface Workspace {
  id: string;
  name: string;
  code: string;
  description: string;
  avatar: AvatarData;
  members: number;
  role: string;
  can_manage: boolean;
  active: boolean;
  switch_url: string;
}
export interface Person {
  id: string;
  name: string;
  email: string;
  avatar: AvatarData;
  role: string;
  role_label: string;
  date: string;
  self?: boolean;
  change_url?: string;
  can_role?: boolean;
  cancel_url?: string;
  share_url?: string;
  resend_url?: string;
  email_sent?: boolean;
}
export interface Team {
  id: string;
  name: string;
  code: string;
  description: string;
  can_manage: boolean;
  is_owner: boolean;
  avatar: AvatarData;
  form: WorkspaceForm | null;
  update_url: string;
  invite_url: string;
  candidates_url: string;
  invite_form: FormSchema | null;
  members: Person[];
  invitations: Person[];
  link_form?: FormSchema;
  link_create_url?: string;
  invite_links?: {
    id: string;
    url: string;
    role: string;
    domain: string;
    date: string;
    uses: number;
    limit: number;
    revoke_url: string;
  }[];
}
export interface Incoming {
  name: string;
  invited_by: string;
  role: string;
  date: string;
  action: string;
  position: number;
  count: number;
  previous: string;
  next: string;
}
export type Tab = 'main' | 'members' | 'invitations';
export interface DirectoryData {
  base_url: string;
  rows: Workspace[];
  create_form: WorkspaceForm;
  create_open: boolean;
  edit_open: boolean;
  tab: Tab;
  team: Team | null;
  invite_open: boolean;
  incoming: Incoming | null;
}
