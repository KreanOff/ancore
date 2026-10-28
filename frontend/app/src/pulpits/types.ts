import type { SummaryWidget } from '../spaces/summaryLayout';
import type { FormDialogData, FormSchema } from '../forms/FormDialog';
import type { PaginationData } from '../shared/Pagination';
import type { EmojiArt } from '../shared/Emoji';
import type { Team } from '../tasks/types';
export type Layout = 'single' | 'equal' | 'left' | 'right' | 'three';
export type SettingsTab = 'gadgets' | 'access' | 'settings';
export interface EditorTab {
  key: SettingsTab;
  label: string;
  icon: string;
  url: string;
  active: boolean;
}
export interface Dashboard {
  id: number;
  slug: string;
  name: string;
  description: string;
  icon: string;
  emoji: string;
  emoji_art: EmojiArt;
  refresh_interval: number;
  author: string;
  visibility: string;
  visibility_label: string;
  layout: Layout;
  revision: number;
  is_default: boolean;
  editable: boolean;
  manageable: boolean;
  deletable: boolean;
  favorite: boolean;
  gadget_count: number;
  url: string;
  edit_url: string;
  access_url: string;
  gadgets_url: string;
  delete_url: string;
  favorite_url: string;
}
export interface Gadget {
  id: number;
  kind: string;
  label: string;
  icon: string;
  edit_url: string;
  delete_url: string;
  unavailable: boolean;
  count?: number;
  closed_count?: number;
  percent?: number;
  statuses?: { key: string; label: string; count: number }[];
  caption?: string;
}
export interface DirectoryData {
  base_url: string;
  list_url: string;
  query: string;
  visibility: string;
  visibility_choices: [string, string][];
  create_url: string;
  results: Dashboard[];
  pagination: PaginationData;
  illustration: string;
  modal: FormDialogData | null;
}
export interface DetailData {
  settings_tabs: EditorTab[];
  dashboard: Dashboard;
  editing: boolean;
  columns: Gadget[][];
  grid: { widgets: SummaryWidget[]; revision: number; save_url: string; columns: number };
  layout_choices: [Layout, string][];
  add_gadget_url: string;
  arrange_url: string;
  quick_add_url: string;
  editor_url: string;
  return_url: string;
  list_url: string;
  max_gadgets: number;
  gadget_catalog: NonNullable<FormSchema['gadget_catalog']>;
  illustration: string;
  column_illustration: string;
  modal: FormDialogData | null;
}
export interface EditData {
  team: Team & { name: string; visibility: string };
  team_url: string;
  settings_tabs: EditorTab[];
  dashboard: Dashboard;
  section: 'access' | 'settings';
  form: FormSchema;
  action: string;
  return_url: string;
}
