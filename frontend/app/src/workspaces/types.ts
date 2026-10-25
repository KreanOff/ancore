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
  is_default: boolean;
  default_url: string;
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
  add_url: string;
  candidates_url: string;
  add_form: FormSchema | null;
  members: Person[];
  link_form?: FormSchema;
  link_create_url?: string;
  invite_links?: {
    id: string;
    url: string;
    role: string;
    date: string;
    uses: number;
    limit: number;
    revoke_url: string;
  }[];
}
export type Tab = 'main' | 'members' | 'links';
export interface DirectoryData {
  base_url: string;
  rows: Workspace[];
  create_form: WorkspaceForm;
  create_open: boolean;
  edit_open: boolean;
  tab: Tab;
  team: Team | null;
  add_open: boolean;
}
