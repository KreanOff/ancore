import type { FormSchema } from '../forms/FormDialog';
export interface Row {
  id: string;
  name: string;
  row_kind?: 'library' | 'folder' | 'document';
  url?: string;
  date: string;
  datetime: string;
  size: string;
  color?: string;
  has_files?: boolean;
  filename?: string;
  kind?: string;
  variant?: string;
  extension?: string;
  created?: string;
  deleted?: string;
  starred?: boolean;
  template?: boolean;
  office_type?: string;
  full_editor?: boolean;
  target?: string;
  location?: string;
  library_name?: string;
  library_url?: string;
  folder_name?: string;
  folder_url?: string;
  edit_url: string;
  delete_url?: string;
  preview_url?: string;
  editor_url?: string;
  download_url?: string;
  star_url?: string;
  trash_url?: string;
  restore_url?: string;
  move_url?: string;
  template_url?: string;
}
export interface DocumentModal {
  title: string;
  action: string;
  return_url: string;
  form: FormSchema | null;
  document: Row | null;
  preview: {
    kind: string;
    note?: string;
    truncated?: boolean;
    text?: string;
    message?: string;
    sheets?: { name: string; rows: { number: number; cells: string[] }[] }[];
    entries?: { name: string; size: number; folder: boolean }[];
  } | null;
  content_url: string;
  location: string;
  upload: boolean;
  office_upload: boolean;
  create_editor: boolean;
  template_create: boolean;
  has_templates: boolean;
  max_size: string;
  color_kind: string;
  default_color: string;
  preview_color: string;
  convert_url: string;
  import_url: string;
}
export interface Filter {
  kind: 'text' | 'choice';
  param: string;
  label: string;
  icon: string;
  value: string;
  active: boolean;
  value_label: string;
  operator: string;
  operator_param: string;
  searchable?: boolean;
  options?: { value: string; label: string }[];
}
export interface DirectoryData {
  office: boolean;
  libraries: boolean;
  base_url: string;
  folder_url: string;
  library: Row | null;
  folder: { id: string; name: string } | null;
  breadcrumbs: { name: string; target: string; url: string }[];
  rows: Row[];
  sidebar: Row[];
  views: {
    value: string;
    label: string;
    icon: string;
    active: boolean;
    url: string;
    count?: number | null;
  }[];
  view: string;
  display: string;
  display_options: { label: string; icon: string; active: boolean; url: string }[];
  query: string;
  filter_params: Record<string, string>;
  filters: Filter[];
  operators: { value: string; label: string }[];
  sort_fields: { value: string; label: string; icon: string; text?: boolean }[];
  sort: string;
  sort_field: string;
  sort_direction: string;
  sort_label: string;
  active_filters: number;
  window: {
    page: number;
    total_pages: number;
    page_size: number;
    page_size_options: number[];
    has_previous: boolean;
    has_next: boolean;
    previous_url: string;
    next_url: string;
    compact_summary: string;
    summary: string;
  };
  return_values: Record<string, string>;
  clear_url: string;
  create_url: string;
  upload_url: string;
  folder_create_url: string;
  template_create_url: string;
  modal: DocumentModal | null;
}
export interface SuiteData {
  document: Row;
  drive: boolean;
  back_url: string;
  revision: number;
  save_receipt: number;
  rename_url: string;
  save_url: string;
  state_url: string;
  board_url: string;
  editor_config: {
    document: { key: string };
    events?: Record<string, unknown>;
    [key: string]: unknown;
  } | null;
  api_url: string;
}
export function bytes(value: number) {
  const unit = value ? Math.min(Math.floor(Math.log(value) / Math.log(1024)), 4) : 0;
  return `${(value / 1024 ** unit).toLocaleString('pl-PL', { maximumFractionDigits: 1 })} ${['B', 'KB', 'MB', 'GB', 'TB'][unit]}`;
}
