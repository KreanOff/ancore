import type { FormDialogData, FormSchema } from '../forms/FormDialog';
import type { Space } from '../spaces/DirectoryPage';
export interface TagNote {
  id: number;
  message: string;
  author: string;
  created_at: string;
  edited_at: string | null;
  editable: boolean;
}
export interface Tag {
  id: number;
  name: string;
  code: string;
  description: string;
  category: string;
  color: string;
  icon: string;
  priority: string;
  scope: string;
  owner_label: string;
  status: string;
  usage_notes: string;
  automation_rules: string;
  related_tags: string[];
  related_label: string;
  task_count: number;
  created_at: string;
  labels: Record<string, string>;
  notes: TagNote[];
}
export interface TagsData {
  space: Space;
  navigation: { key: string; label: string; icon: string; url: string }[];
  can_edit: boolean;
  form: FormSchema | null;
  modal: FormDialogData | null;
  tags: Tag[];
  query: string;
  filters: Record<string, string>;
  filter_options: Record<string, { value: string; label: string }[]>;
  sort: string;
  sort_options: { value: string; label: string; icon: string; direction: string }[];
  window: {
    page: number;
    total_pages: number;
    total_tags: number;
    page_size: number;
    page_size_options: number[];
    previous_url: string;
    next_url: string;
    summary: string;
    compact_summary: string;
  };
}
