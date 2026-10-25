import type { FormSchema } from '../forms/FormDialog';
import type { AvatarData } from '../shared/Avatar';
import type { AvatarForm } from '../shared/AvatarControl';
export interface AuthData {
  mode: 'login' | 'register' | 'workspace' | 'add';
  form: FormSchema;
  urls: Record<string, string>;
  logo: string;
  has_workspaces?: boolean;
}
export interface WorkspacePickerData {
  workspaces: { id: string; name: string; switch_url: string }[];
  urls: { home: string; create: string; login: string };
}
export interface ProfileData {
  user: {
    name: string;
    first_name: string;
    middle_name: string;
    last_name: string;
    email: string;
    username: string;
    phone_number: string;
    job_title: string;
    bio: string;
    avatar: AvatarData;
    presence_status: string;
    active: boolean;
    role: string;
    joined: string;
    last_login: string;
  };
  form: AvatarForm;
  accounts: {
    id: string;
    name: string;
    email: string;
    username: string;
    current: boolean;
    avatar: AvatarData;
    presence_status: string;
    presence_label: string;
  }[];
  urls: Record<string, string>;
}
