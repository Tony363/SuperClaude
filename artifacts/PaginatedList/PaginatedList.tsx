import React, { useCallback, useRef, useEffect } from 'react';
import type { BaseItem, PaginatedListProps, ErrorInfo } from './types';
import { usePagination } from './usePagination';
import { PaginationControls } from './PaginationControls';

/**
 * Default loading skeleton component
 */
function DefaultLoadingSkeleton(): React.ReactElement {
  return (
    <div className="space-y-4 animate-pulse" aria-busy="true" aria-label="Loading items">
      {[...Array(5)].map((_, index) => (
        <div key={index} className="flex items-center space-x-4">
          <div className="w-12 h-12 bg-gray-200 rounded-full" />
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-gray-200 rounded w-3/4" />
            <div className="h-3 bg-gray-200 rounded w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Default error component with retry capability
 */
function DefaultErrorComponent({
  error,
  retry,
}: {
  error: ErrorInfo;
  retry: () => void;
}): React.ReactElement {
  return (
    <div
      className="flex flex-col items-center justify-center p-8 text-center"
      role="alert"
      aria-live="assertive"
    >
      <svg
        className="w-16 h-16 text-red-500 mb-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">Something went wrong</h3>
      <p className="text-gray-600 mb-4 max-w-md">{error.message}</p>
      {error.code && (
        <p className="text-sm text-gray-500 mb-4">Error code: {error.code}</p>
      )}
      {error.retryable && (
        <button
          type="button"
          onClick={retry}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
        >
          Try again
        </button>
      )}
    </div>
  );
}

/**
 * Default empty state component
 */
function DefaultEmptyComponent(): React.ReactElement {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <svg
        className="w-16 h-16 text-gray-400 mb-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
        />
      </svg>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">No items found</h3>
      <p className="text-gray-600">There are no items to display at this time.</p>
    </div>
  );
}

/**
 * PaginatedList - A reusable component for displaying paginated data
 *
 * Features:
 * - Generic type support for any item type
 * - Loading, error, and empty states
 * - Accessible keyboard navigation
 * - Customizable rendering
 * - Responsive design
 */
export function PaginatedList<T extends BaseItem>({
  fetchItems,
  renderItem,
  pageSize = 10,
  initialPage = 1,
  loadingComponent,
  errorComponent,
  emptyComponent,
  className = '',
  ariaLabel = 'Paginated list',
  keyboardNavigation = true,
}: PaginatedListProps<T>): React.ReactElement {
  const {
    items,
    meta,
    loadingState,
    error,
    goToPage,
    retry,
  } = usePagination<T>({
    fetchItems,
    pageSize,
    initialPage,
  });

  const listRef = useRef<HTMLUListElement>(null);
  const focusedIndexRef = useRef<number>(-1);

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!keyboardNavigation || items.length === 0) return;

    const listElement = listRef.current;
    if (!listElement) return;

    const focusableItems = listElement.querySelectorAll<HTMLElement>('[tabindex="0"]');
    const currentIndex = focusedIndexRef.current;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        if (currentIndex < focusableItems.length - 1) {
          focusedIndexRef.current = currentIndex + 1;
          focusableItems[focusedIndexRef.current]?.focus();
        }
        break;
      case 'ArrowUp':
        e.preventDefault();
        if (currentIndex > 0) {
          focusedIndexRef.current = currentIndex - 1;
          focusableItems[focusedIndexRef.current]?.focus();
        }
        break;
      case 'Home':
        e.preventDefault();
        focusedIndexRef.current = 0;
        focusableItems[0]?.focus();
        break;
      case 'End':
        e.preventDefault();
        focusedIndexRef.current = focusableItems.length - 1;
        focusableItems[focusableItems.length - 1]?.focus();
        break;
    }
  }, [keyboardNavigation, items.length]);

  // Reset focus when items change
  useEffect(() => {
    focusedIndexRef.current = -1;
  }, [items]);

  // Render loading state
  if (loadingState === 'loading' && items.length === 0) {
    return (
      <div className={className} aria-busy="true">
        {loadingComponent || <DefaultLoadingSkeleton />}
      </div>
    );
  }

  // Render error state
  if (loadingState === 'error' && error) {
    return (
      <div className={className}>
        {errorComponent ? (
          errorComponent(error, retry)
        ) : (
          <DefaultErrorComponent error={error} retry={retry} />
        )}
      </div>
    );
  }

  // Render empty state
  if (loadingState === 'success' && items.length === 0) {
    return (
      <div className={className}>
        {emptyComponent || <DefaultEmptyComponent />}
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Loading overlay for subsequent page loads */}
      {loadingState === 'loading' && items.length > 0 && (
        <div
          className="absolute inset-0 bg-white/50 flex items-center justify-center"
          aria-hidden="true"
        >
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Item list */}
      <ul
        ref={listRef}
        className="divide-y divide-gray-200 relative"
        role="list"
        aria-label={ariaLabel}
        onKeyDown={handleKeyDown}
      >
        {items.map((item, index) => (
          <li
            key={item.id}
            className="py-4 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
            tabIndex={keyboardNavigation ? 0 : -1}
            onFocus={() => { focusedIndexRef.current = index; }}
          >
            {renderItem(item, index)}
          </li>
        ))}
      </ul>

      {/* Pagination controls */}
      {meta && meta.totalPages > 1 && (
        <PaginationControls
          meta={meta}
          onPageChange={goToPage}
          disabled={loadingState === 'loading'}
        />
      )}
    </div>
  );
}

export default PaginatedList;
