import { useState, useCallback, useEffect, useRef } from 'react';
import type { FetchParams, FetchResult, LoadingState, PaginationConfig } from './types';

interface UsePaginationOptions<T> extends PaginationConfig {
  fetchData: (params: FetchParams) => Promise<FetchResult<T>>;
}

interface UsePaginationReturn<T> {
  items: T[];
  currentPage: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  loadingState: LoadingState;
  error: Error | null;
  goToPage: (page: number) => void;
  nextPage: () => void;
  prevPage: () => void;
  setPageSize: (size: number) => void;
  refresh: () => void;
}

export function usePagination<T>({
  fetchData,
  initialPage = 1,
  pageSize: initialPageSize = 10,
}: UsePaginationOptions<T>): UsePaginationReturn<T> {
  const [items, setItems] = useState<T[]>([]);
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [pageSize, setPageSizeState] = useState(initialPageSize);
  const [totalItems, setTotalItems] = useState(0);
  const [loadingState, setLoadingState] = useState<LoadingState>('idle');
  const [error, setError] = useState<Error | null>(null);

  // Abort controller for cancelling in-flight requests
  const abortControllerRef = useRef<AbortController | null>(null);

  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));

  const fetchPage = useCallback(
    async (page: number, size: number) => {
      // Cancel any in-flight request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      setLoadingState('loading');
      setError(null);

      try {
        const result = await fetchData({
          page,
          pageSize: size,
        });

        // Check if request was aborted
        if (abortControllerRef.current?.signal.aborted) {
          return;
        }

        setItems(result.items);
        setTotalItems(result.totalItems);
        setLoadingState('success');
      } catch (err) {
        // Ignore abort errors
        if (err instanceof Error && err.name === 'AbortError') {
          return;
        }

        setError(err instanceof Error ? err : new Error('Failed to fetch data'));
        setLoadingState('error');
      }
    },
    [fetchData]
  );

  // Fetch data when page or pageSize changes
  useEffect(() => {
    fetchPage(currentPage, pageSize);

    return () => {
      // Cleanup: abort on unmount or before next fetch
      abortControllerRef.current?.abort();
    };
  }, [currentPage, pageSize, fetchPage]);

  const goToPage = useCallback(
    (page: number) => {
      const validPage = Math.max(1, Math.min(page, totalPages || 1));
      setCurrentPage(validPage);
    },
    [totalPages]
  );

  const nextPage = useCallback(() => {
    if (currentPage < totalPages) {
      setCurrentPage((prev) => prev + 1);
    }
  }, [currentPage, totalPages]);

  const prevPage = useCallback(() => {
    if (currentPage > 1) {
      setCurrentPage((prev) => prev - 1);
    }
  }, [currentPage]);

  const setPageSize = useCallback((size: number) => {
    setPageSizeState(size);
    setCurrentPage(1); // Reset to first page when changing page size
  }, []);

  const refresh = useCallback(() => {
    fetchPage(currentPage, pageSize);
  }, [currentPage, pageSize, fetchPage]);

  return {
    items,
    currentPage,
    pageSize,
    totalItems,
    totalPages,
    loadingState,
    error,
    goToPage,
    nextPage,
    prevPage,
    setPageSize,
    refresh,
  };
}
