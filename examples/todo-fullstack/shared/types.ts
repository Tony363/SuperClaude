/**
 * Shared Todo Types - Contract between Frontend and Backend
 */

export interface Todo {
  id: string;
  title: string;
  completed: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface CreateTodoRequest {
  title: string;
}

export interface UpdateTodoRequest {
  title?: string;
  completed?: boolean;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

export type TodoListResponse = ApiResponse<Todo[]>;
export type TodoResponse = ApiResponse<Todo>;
