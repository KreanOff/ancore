export interface PaginationData {
  page: number;
  count: number;
  start: number;
  end: number;
  previous: string;
  next: string;
  pages: { label: string; url: string; current: boolean }[];
}
