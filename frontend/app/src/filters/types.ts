import type { FormDialogData, FormSchema } from '../forms/FormDialog';
import type { PaginationData } from '../shared/Pagination';
import type { Item } from '../spaces/types';
export interface SavedFilter {
  id: number;
  name: string;
  description: string;
  query: string;
  author: string;
  visibility: string;
  visibility_label: string;
  revision: number;
  favorite: boolean;
  editable: boolean;
  url: string;
  edit_url: string;
  favorite_url: string;
  delete_url: string;
}
export interface DirectoryData {
  tab: string;
  query: string;
  filters_url: string;
  search_url: string;
  list_url: string;
  results: SavedFilter[];
  pagination: PaginationData;
  illustration: string;
  modal: FormDialogData | null;
}
export interface SearchData {
  jql: string;
  search_error: string;
  mode: 'basic' | 'advanced';
  basic_available: boolean;
  changed: boolean;
  can_save: boolean;
  search_url: string;
  filters_url: string;
  list_url: string;
  clear_url: string;
  save_as_url: string;
  basic_url: string;
  advanced_url: string;
  saved_filter: SavedFilter | null;
  form: FormSchema;
  items: Item[];
  pagination: PaginationData;
  modal: FormDialogData | null;
}
