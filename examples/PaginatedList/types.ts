/**
 * TypeScript types for the PaginatedList component
 */

export interface PaginationState {
  currentPage: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
}

export interface PaginationConfig {
  initialPage?: number;
  pageSize?: number;
  pageSizeOptions?: number[];
  showPageSizeSelector?: boolean;
  showPageNumbers?: boolean;
  maxPageButtons?: number;
}

export interface FetchParams {
  page: number;
  pageSize: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  filters?: Record<string, unknown>;
}

export interface FetchResult<T> {
  items: T[];
  totalItems: number;
  currentPage: number;
  pageSize: number;
}

export interface PaginatedListProps<T> {
  /** Function to fetch paginated data */
  fetchData: (params: FetchParams) => Promise<FetchResult<T>>;
  /** Render function for each item */
  renderItem: (item: T, index: number) => React.ReactNode;
  /** Unique key extractor for list items */
  keyExtractor: (item: T) => string | number;
  /** Pagination configuration */
  paginationConfig?: PaginationConfig;
  /** Custom loading component */
  LoadingComponent?: React.ComponentType;
  /** Custom error component */
  ErrorComponent?: React.ComponentType<{ error: Error; retry: () => void }>;
  /** Custom empty state component */
  EmptyComponent?: React.ComponentType;
  /** Additional CSS class for container */
  className?: string;
  /** Accessible label for the list */
  ariaLabel?: string;
}

export interface PaginationControlsProps {
  currentPage: number;
  totalPages: number;
  pageSize: number;
  totalItems: number;
  pageSizeOptions: number[];
  showPageSizeSelector: boolean;
  showPageNumbers: boolean;
  maxPageButtons: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
  isLoading: boolean;
}

export type LoadingState = 'idle' | 'loading' | 'success' | 'error';
