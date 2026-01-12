/**
 * TypeScript types for the PaginatedList component
 */

/** Generic item type - extend this for your specific data */
export interface BaseItem {
  id: string | number;
}

/** Pagination metadata */
export interface PaginationMeta {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  itemsPerPage: number;
  hasNextPage: boolean;
  hasPreviousPage: boolean;
}

/** Loading states for better UX */
export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

/** Error information */
export interface ErrorInfo {
  message: string;
  code?: string | number;
  retryable?: boolean;
}

/** Paginated response from API */
export interface PaginatedResponse<T extends BaseItem> {
  items: T[];
  meta: PaginationMeta;
}

/** Props for the PaginatedList component */
export interface PaginatedListProps<T extends BaseItem> {
  /** Function to fetch items for a given page */
  fetchItems: (page: number, pageSize: number) => Promise<PaginatedResponse<T>>;
  /** Render function for each item */
  renderItem: (item: T, index: number) => React.ReactNode;
  /** Number of items per page */
  pageSize?: number;
  /** Initial page to load */
  initialPage?: number;
  /** Custom loading component */
  loadingComponent?: React.ReactNode;
  /** Custom error component */
  errorComponent?: (error: ErrorInfo, retry: () => void) => React.ReactNode;
  /** Custom empty state component */
  emptyComponent?: React.ReactNode;
  /** CSS class for the list container */
  className?: string;
  /** Accessible label for the list */
  ariaLabel?: string;
  /** Enable keyboard navigation */
  keyboardNavigation?: boolean;
}

/** Props for the Pagination controls */
export interface PaginationControlsProps {
  meta: PaginationMeta;
  onPageChange: (page: number) => void;
  disabled?: boolean;
  showPageNumbers?: boolean;
  maxVisiblePages?: number;
  className?: string;
}

/** Hook return type */
export interface UsePaginationReturn<T extends BaseItem> {
  items: T[];
  meta: PaginationMeta | null;
  loadingState: LoadingState;
  error: ErrorInfo | null;
  currentPage: number;
  goToPage: (page: number) => void;
  goToNextPage: () => void;
  goToPreviousPage: () => void;
  retry: () => void;
  refresh: () => void;
}
