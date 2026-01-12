import { useState, useCallback, useEffect, useRef } from 'react';
import type {
  BaseItem,
  PaginatedResponse,
  PaginationMeta,
  LoadingState,
  ErrorInfo,
  UsePaginationReturn,
} from './types';

interface UsePaginationOptions<T extends BaseItem> {
  fetchItems: (page: number, pageSize: number) => Promise<PaginatedResponse<T>>;
  pageSize: number;
  initialPage: number;
}

/**
 * Custom hook for managing pagination state and data fetching
 * Handles loading states, errors, and page navigation
 */
export function usePagination<T extends BaseItem>({
  fetchItems,
  pageSize,
  initialPage,
}: UsePaginationOptions<T>): UsePaginationReturn<T> {
  const [items, setItems] = useState<T[]>([]);
  const [meta, setMeta] = useState<PaginationMeta | null>(null);
  const [loadingState, setLoadingState] = useState<LoadingState>('idle');
  const [error, setError] = useState<ErrorInfo | null>(null);
  const [currentPage, setCurrentPage] = useState(initialPage);

  // Track the current request to prevent race conditions
  const requestIdRef = useRef(0);
  // Track if component is mounted
  const isMountedRef = useRef(true);

  const loadPage = useCallback(async (page: number) => {
    const requestId = ++requestIdRef.current;

    setLoadingState('loading');
    setError(null);

    try {
      const response = await fetchItems(page, pageSize);

      // Only update state if this is the most recent request and component is mounted
      if (requestId === requestIdRef.current && isMountedRef.current) {
        setItems(response.items);
        setMeta(response.meta);
        setLoadingState('success');
        setCurrentPage(page);
      }
    } catch (err) {
      if (requestId === requestIdRef.current && isMountedRef.current) {
        const errorInfo: ErrorInfo = {
          message: err instanceof Error ? err.message : 'An error occurred while fetching items',
          retryable: true,
        };

        if (err instanceof Error && 'code' in err) {
          errorInfo.code = (err as Error & { code: string | number }).code;
        }

        setError(errorInfo);
        setLoadingState('error');
      }
    }
  }, [fetchItems, pageSize]);

  // Initial load
  useEffect(() => {
    loadPage(initialPage);
  }, [loadPage, initialPage]);

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const goToPage = useCallback((page: number) => {
    if (meta && page >= 1 && page <= meta.totalPages) {
      loadPage(page);
    }
  }, [meta, loadPage]);

  const goToNextPage = useCallback(() => {
    if (meta?.hasNextPage) {
      goToPage(currentPage + 1);
    }
  }, [meta, currentPage, goToPage]);

  const goToPreviousPage = useCallback(() => {
    if (meta?.hasPreviousPage) {
      goToPage(currentPage - 1);
    }
  }, [meta, currentPage, goToPage]);

  const retry = useCallback(() => {
    loadPage(currentPage);
  }, [loadPage, currentPage]);

  const refresh = useCallback(() => {
    loadPage(currentPage);
  }, [loadPage, currentPage]);

  return {
    items,
    meta,
    loadingState,
    error,
    currentPage,
    goToPage,
    goToNextPage,
    goToPreviousPage,
    retry,
    refresh,
  };
}
