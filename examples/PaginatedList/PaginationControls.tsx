import React, { useMemo } from 'react';
import type { PaginationControlsProps } from './types';

/**
 * Generates an array of page numbers to display, with ellipsis for gaps
 */
function getPageNumbers(
  currentPage: number,
  totalPages: number,
  maxButtons: number
): (number | 'ellipsis')[] {
  if (totalPages <= maxButtons) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  const pages: (number | 'ellipsis')[] = [];
  const sideButtons = Math.floor((maxButtons - 3) / 2); // -3 for first, last, and current

  // Always show first page
  pages.push(1);

  const startPage = Math.max(2, currentPage - sideButtons);
  const endPage = Math.min(totalPages - 1, currentPage + sideButtons);

  // Add ellipsis if there's a gap after first page
  if (startPage > 2) {
    pages.push('ellipsis');
  }

  // Add middle pages
  for (let i = startPage; i <= endPage; i++) {
    pages.push(i);
  }

  // Add ellipsis if there's a gap before last page
  if (endPage < totalPages - 1) {
    pages.push('ellipsis');
  }

  // Always show last page
  if (totalPages > 1) {
    pages.push(totalPages);
  }

  return pages;
}

export const PaginationControls: React.FC<PaginationControlsProps> = ({
  currentPage,
  totalPages,
  pageSize,
  totalItems,
  pageSizeOptions,
  showPageSizeSelector,
  showPageNumbers,
  maxPageButtons,
  onPageChange,
  onPageSizeChange,
  isLoading,
}) => {
  const pageNumbers = useMemo(
    () => getPageNumbers(currentPage, totalPages, maxPageButtons),
    [currentPage, totalPages, maxPageButtons]
  );

  const startItem = (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalItems);

  const handleKeyDown = (
    event: React.KeyboardEvent,
    action: () => void
  ) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      action();
    }
  };

  return (
    <nav
      className="pagination-controls"
      role="navigation"
      aria-label="Pagination"
    >
      {/* Results summary */}
      <div className="pagination-info" aria-live="polite">
        {totalItems > 0 ? (
          <span>
            Showing {startItem}–{endItem} of {totalItems} items
          </span>
        ) : (
          <span>No items</span>
        )}
      </div>

      <div className="pagination-actions">
        {/* Page size selector */}
        {showPageSizeSelector && (
          <div className="page-size-selector">
            <label htmlFor="page-size-select">Items per page:</label>
            <select
              id="page-size-select"
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              disabled={isLoading}
              aria-label="Select number of items per page"
            >
              {pageSizeOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Navigation buttons */}
        <div className="pagination-nav" role="group" aria-label="Page navigation">
          {/* Previous button */}
          <button
            type="button"
            className="pagination-btn pagination-btn--prev"
            onClick={() => onPageChange(currentPage - 1)}
            onKeyDown={(e) => handleKeyDown(e, () => onPageChange(currentPage - 1))}
            disabled={currentPage === 1 || isLoading}
            aria-label="Go to previous page"
          >
            <span aria-hidden="true">←</span>
            <span className="sr-only">Previous</span>
          </button>

          {/* Page numbers */}
          {showPageNumbers && (
            <div className="pagination-pages" role="group" aria-label="Page numbers">
              {pageNumbers.map((page, index) =>
                page === 'ellipsis' ? (
                  <span
                    key={`ellipsis-${index}`}
                    className="pagination-ellipsis"
                    aria-hidden="true"
                  >
                    …
                  </span>
                ) : (
                  <button
                    key={page}
                    type="button"
                    className={`pagination-btn pagination-btn--page ${
                      page === currentPage ? 'pagination-btn--active' : ''
                    }`}
                    onClick={() => onPageChange(page)}
                    disabled={isLoading}
                    aria-label={`Page ${page}`}
                    aria-current={page === currentPage ? 'page' : undefined}
                  >
                    {page}
                  </button>
                )
              )}
            </div>
          )}

          {/* Next button */}
          <button
            type="button"
            className="pagination-btn pagination-btn--next"
            onClick={() => onPageChange(currentPage + 1)}
            onKeyDown={(e) => handleKeyDown(e, () => onPageChange(currentPage + 1))}
            disabled={currentPage === totalPages || isLoading}
            aria-label="Go to next page"
          >
            <span className="sr-only">Next</span>
            <span aria-hidden="true">→</span>
          </button>
        </div>
      </div>
    </nav>
  );
};
