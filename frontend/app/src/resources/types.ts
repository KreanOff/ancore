export interface Resource {
  id: number;
  name: string;
  inventory_number: string;
  serial_number: string;
  kind: string;
  status: string;
  kind_label: string;
  status_label: string;
  assigned_to: number | '';
  assignee_name: string;
  location: string;
  notes: string;
  purchased_on: string;
  expires_on: string;
  overdue: boolean;
  icon: string;
}
export interface Avatar {
  photo_url: string;
  preset_class?: string;
  color_class: string;
  background_color: string;
  foreground_color: string;
}
export interface Field {
  name: string;
  label: string;
  required: boolean;
  help_text: string;
  value: string;
  type: 'text' | 'date' | 'textarea' | 'select';
  max_length?: number;
  placeholder: string;
  choices?: { value: string; label: string; avatar?: Avatar }[];
}
export interface Editor {
  id: number | null;
  fields: Field[];
}
export type Errors = Record<string, { message: string; code: string }[]>;
export interface Directory {
  results: Resource[];
  list_url: string;
  base_url: string;
  api_url: string;
  query: string;
  has_filters: boolean;
  sort: string;
  sort_label: string;
  filters: {
    name: string;
    label: string;
    icon: string;
    value: string;
    selected_label: string;
    options: [string, string][];
  }[];
  sort_options: [string, string][];
  pagination: {
    page: number;
    total_pages: number;
    page_size: number;
    page_size_options: number[];
    summary: string;
    has_previous: boolean;
    has_next: boolean;
    previous_url: string;
    next_url: string;
  };
  editor?: Editor;
}
