import React from 'react';
import { usePagination } from './usePagination';
import { PaginationControls } from './PaginationControls';
import type { PaginatedListProps } from './types';

// Default loading component with skeleton animation
const DefaultLoadingComponent: React.FC = () => (
  <div className="paginated-list__loading" role="status" aria-label="Loading">
    <div className="loading-spinner" aria-hidden="true" />
    <span className="loading-text">Loading items...</span>
    <div className="skeleton-list" aria-hidden="true">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="skeleton-item" />
      ))}
    </div>
  </div>
);

// Default error component with retry button
const DefaultErrorComponent: React.FC<{ error: Error; retry: () => void }> = ({
  error,
  retry,
}) => (
  <div
    className="paginated-list__error"
    role="alert"
    aria-live="assertive"
  >
    <div className="error-icon" aria-hidden="true">⚠</div>
    <h3 className="error-title">Failed to load items</h3>
    <p className="error-message">{error.message}</p>
    <button
      type="button"
      className="error-retry-btn"
      onClick={retry}
      aria-label="Retry loading items"
    >
      Try Again
    </button>
  </div>
);

// Default empty state component
const DefaultEmptyComponent: React.FC = () => (
  <div className="paginated-list__empty" role="status">
    <div className="empty-icon" aria-hidden="true">📋</div>
    <h3 className="empty-title">No items found</h3>
    <p className="empty-message">There are no items to display.</p>
  </div>
);

export function PaginatedList<T>({
  fetchData,
  renderItem,
  keyExtractor,
  paginationConfig = {},
  LoadingComponent = DefaultLoadingComponent,
  ErrorComponent = DefaultErrorComponent,
  EmptyComponent = DefaultEmptyComponent,
  className = '',
  ariaLabel = 'Paginated list',
}: PaginatedListProps<T>): React.ReactElement {
  const {
    initialPage = 1,
    pageSize: configPageSize = 10,
    pageSizeOptions = [10, 25, 50, 100],
    showPageSizeSelector = true,
    showPageNumbers = true,
    maxPageButtons = 7,
  } = paginationConfig;

  const {
    items,
    currentPage,
    pageSize,
    totalItems,
    totalPages,
    loadingState,
    error,
    goToPage,
    setPageSize,
    refresh,
  } = usePagination({
    fetchData,
    initialPage,
    pageSize: configPageSize,
  });

  const isLoading = loadingState === 'loading';
  const hasError = loadingState === 'error';
  const isEmpty = loadingState === 'success' && items.length === 0;
  const hasItems = loadingState === 'success' && items.length > 0;

  return (
    <div
      className={`paginated-list ${className}`.trim()}
      aria-label={ariaLabel}
    >
      {/* Loading state */}
      {isLoading && <LoadingComponent />}

      {/* Error state */}
      {hasError && error && (
        <ErrorComponent error={error} retry={refresh} />
      )}

      {/* Empty state */}
      {isEmpty && <EmptyComponent />}

      {/* List items */}
      {hasItems && (
        <>
          <ul
            className="paginated-list__items"
            role="list"
            aria-label={`${ariaLabel} - Page ${currentPage} of ${totalPages}`}
          >
            {items.map((item, index) => (
              <li
                key={keyExtractor(item)}
                className="paginated-list__item"
                role="listitem"
              >
                {renderItem(item, index)}
              </li>
            ))}
          </ul>

          {/* Pagination controls */}
          <PaginationControls
            currentPage={currentPage}
            totalPages={totalPages}
            pageSize={pageSize}
            totalItems={totalItems}
            pageSizeOptions={pageSizeOptions}
            showPageSizeSelector={showPageSizeSelector}
            showPageNumbers={showPageNumbers}
            maxPageButtons={maxPageButtons}
            onPageChange={goToPage}
            onPageSizeChange={setPageSize}
            isLoading={isLoading}
          />
        </>
      )}
    </div>
  );
}

export default PaginatedList;
