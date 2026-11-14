import type { FormSchema } from '../forms/FormDialog';
import type { AvatarData } from '../shared/Avatar';
import type { AvatarForm } from '../shared/AvatarControl';
import type { BannerCrop } from './banner-crop';
export interface AuthData {
  mode: 'login' | 'register' | 'workspace';
  form: FormSchema;
  urls: Record<string, string>;
  logo: string;
  has_workspaces?: boolean;
}
export interface WorkspacePickerData {
  workspaces: { id: string; name: string; avatar: AvatarData; switch_url: string }[];
  urls: { home: string; create: string; logout: string };
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
  banner: { url: string; default_url: string; custom: boolean; max_size: number; crop: BannerCrop };
  banner_form: FormSchema;
  form: AvatarForm;
  urls: Record<string, string>;
}
