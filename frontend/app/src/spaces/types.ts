import type { AvatarData } from '../shared/Avatar';
import type { PaginationData } from '../shared/Pagination';
import type { FormDialogData } from '../forms/FormDialog';
import type { Space } from './DirectoryPage';
export interface Status {
  key: string;
  label: string;
  category: string;
  count: number;
  loaded_count?: number;
  more_url?: string;
}
export interface Item {
  id: number;
  task_id: number;
  key: string;
  title: string;
  url: string;
  edit_url: string;
  action_url: string;
  editable: boolean;
  rank: number;
  sprint_id: number | null;
  status: string;
  status_label: string;
  category: string;
  status_order: number;
  transitions: Status[];
  priority: string;
  priority_label: string;
  work_type: string;
  type_label: string;
  type_icon: string;
  points: number | null;
  in_backlog: boolean;
  assignee: { label: string; avatar: AvatarData } | null;
  team: string;
  tags_count: number;
  attachments_count: number;
  due_at: string | null;
  due_urgency: string;
  start_on: string | null;
  timeline: { start: string; end: string; left: string; width: string };
}
export interface Totals {
  total: number;
  points: number;
  finished: number;
  finished_points: number;
  unestimated: number;
}
export interface Sprint {
  id: number;
  name: string;
  goal: string;
  state: string;
  state_label: string;
  start_on: string;
  end_on: string;
  action_url: string;
  edit_url: string;
  start_url: string;
  complete_url: string;
  create_item_url: string;
  planning: Totals;
  visible_count: number;
  finished_count: number;
  loaded_count: number;
  more_url: string;
}
interface Distribution {
  key?: string;
  label: string;
  count: number;
  percent: number;
  url: string;
  icon?: string;
  avatar?: AvatarData;
}
export interface Summary {
  dashboard: import('./SummaryDashboard').SummaryDashboardData;
  metrics: { key: string; label: string; icon: string; count: number; url: string }[];
  list_url: string;
  total: number;
  status_total: number;
  open_total: number;
  statuses: (Status & { url: string; path: string; arc: string; gap: string; offset: string })[];
  activities: {
    id: number;
    url: string;
    avatar: AvatarData;
    actor: string;
    action: string;
    key: string;
    title: string;
    created_at: string;
  }[];
  priority_axis: { max: number; middle: number };
  priorities: { key: string; label: string; count: number; url: string; height: string }[];
  types: Distribution[];
  workload: Distribution[];
  epics: {
    url: string;
    key: string;
    title: string;
    closed: number;
    total: number;
    percent: number;
  }[];
}
export interface DetailData {
  team: import('../tasks/types').Team;
  team_url: string;
  space: Space;
  view: string;
  navigation: { key: string; label: string; icon: string; url: string }[];
  can_manage: boolean;
  can_configure: boolean;
  can_edit: boolean;
  create_item_url: string;
  sprint_create_url: string;
  edit_url: string;
  configuration_url: string;
  member_url: string;
  bulk_plan_url: string;
  backlog_create_url: string;
  configuration: { name: string; shared: boolean };
  summary: Summary | null;
  items: Item[];
  stats: { all: number; closed: number; overdue: number; points: number };
  status_counts: Status[];
  columns: Status[];
  sprints: Sprint[];
  active_sprint: Sprint | null;
  backlog_totals: Totals;
  backlog_loaded_count: number;
  backlog_more_url: string;
  timeline: { start: string; end: string } | null;
  pagination: PaginationData | null;
  filters: Record<string, string>;
  sort: {
    value: string;
    field: string;
    direction: string;
    label: string;
    manual: boolean;
    default: string;
    fields: { value: string; label: string; icon: string }[];
  };
  summary_filter_label: string;
  filter_options: Record<string, [string, string][]>;
  members: {
    id: number;
    name: string;
    avatar: AvatarData;
    role: string;
    can_remove: boolean;
    remove_url: string;
  }[];
  private_owner: string;
  modal: FormDialogData | null;
}
export function dateLabel(value: string | null, time = false) {
  return value
    ? new Date(value).toLocaleString(
        'pl-PL',
        time
          ? {
              timeZone: 'Europe/Warsaw',
              day: '2-digit',
              month: '2-digit',
              year: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            }
          : { timeZone: 'Europe/Warsaw', day: '2-digit', month: '2-digit', year: 'numeric' },
      )
    : '';
}
