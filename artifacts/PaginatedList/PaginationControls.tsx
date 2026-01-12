import React, { useMemo } from 'react';
import type { PaginationControlsProps } from './types';

/**
 * Pagination controls component with accessible navigation
 * Supports keyboard navigation and screen readers
 */
export function PaginationControls({
  meta,
  onPageChange,
  disabled = false,
  showPageNumbers = true,
  maxVisiblePages = 5,
  className = '',
}: PaginationControlsProps): React.ReactElement {
  const { currentPage, totalPages, totalItems, itemsPerPage } = meta;

  // Calculate the range of items being displayed
  const startItem = (currentPage - 1) * itemsPerPage + 1;
  const endItem = Math.min(currentPage * itemsPerPage, totalItems);

  // Generate array of page numbers to display
  const pageNumbers = useMemo(() => {
    if (!showPageNumbers || totalPages <= 1) return [];

    const pages: (number | 'ellipsis')[] = [];
    const half = Math.floor(maxVisiblePages / 2);

    let start = Math.max(1, currentPage - half);
    let end = Math.min(totalPages, currentPage + half);

    // Adjust range if at the edges
    if (currentPage <= half) {
      end = Math.min(totalPages, maxVisiblePages);
    } else if (currentPage > totalPages - half) {
      start = Math.max(1, totalPages - maxVisiblePages + 1);
    }

    // Always show first page
    if (start > 1) {
      pages.push(1);
      if (start > 2) pages.push('ellipsis');
    }

    // Add middle pages
    for (let i = start; i <= end; i++) {
      if (i !== 1 && i !== totalPages) {
        pages.push(i);
      }
    }

    // Always show last page
    if (end < totalPages) {
      if (end < totalPages - 1) pages.push('ellipsis');
      pages.push(totalPages);
    }

    // Handle case where totalPages equals 1
    if (totalPages === 1) {
      return [1];
    }

    return pages;
  }, [currentPage, totalPages, maxVisiblePages, showPageNumbers]);

  const handleKeyDown = (e: React.KeyboardEvent, action: () => void) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      action();
    }
  };

  const buttonBaseClass = `
    px-3 py-2
    text-sm font-medium
    rounded-md
    transition-colors duration-150
    focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
  `;

  const activeButtonClass = `
    ${buttonBaseClass}
    bg-blue-600 text-white
  `;

  const inactiveButtonClass = `
    ${buttonBaseClass}
    bg-white text-gray-700
    hover:bg-gray-50
    border border-gray-300
    disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-white
  `;

  return (
    <nav
      className={`flex flex-col sm:flex-row items-center justify-between gap-4 ${className}`}
      aria-label="Pagination navigation"
      role="navigation"
    >
      {/* Item count display */}
      <p className="text-sm text-gray-700" aria-live="polite">
        Showing <span className="font-medium">{startItem}</span> to{' '}
        <span className="font-medium">{endItem}</span> of{' '}
        <span className="font-medium">{totalItems}</span> results
      </p>

      {/* Navigation controls */}
      <div className="flex items-center gap-1" role="group" aria-label="Page navigation">
        {/* Previous button */}
        <button
          type="button"
          onClick={() => onPageChange(currentPage - 1)}
          onKeyDown={(e) => handleKeyDown(e, () => onPageChange(currentPage - 1))}
          disabled={disabled || !meta.hasPreviousPage}
          className={inactiveButtonClass}
          aria-label="Go to previous page"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        {/* Page numbers */}
        {showPageNumbers && pageNumbers.length > 0 && (
          <div className="hidden sm:flex items-center gap-1">
            {pageNumbers.map((page, index) =>
              page === 'ellipsis' ? (
                <span
                  key={`ellipsis-${index}`}
                  className="px-3 py-2 text-gray-500"
                  aria-hidden="true"
                >
                  ...
                </span>
              ) : (
                <button
                  key={page}
                  type="button"
                  onClick={() => onPageChange(page)}
                  disabled={disabled}
                  className={page === currentPage ? activeButtonClass : inactiveButtonClass}
                  aria-label={`Go to page ${page}`}
                  aria-current={page === currentPage ? 'page' : undefined}
                >
                  {page}
                </button>
              )
            )}
          </div>
        )}

        {/* Mobile page indicator */}
        <span className="sm:hidden px-3 py-2 text-sm text-gray-700">
          Page {currentPage} of {totalPages}
        </span>

        {/* Next button */}
        <button
          type="button"
          onClick={() => onPageChange(currentPage + 1)}
          onKeyDown={(e) => handleKeyDown(e, () => onPageChange(currentPage + 1))}
          disabled={disabled || !meta.hasNextPage}
          className={inactiveButtonClass}
          aria-label="Go to next page"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </nav>
  );
}
