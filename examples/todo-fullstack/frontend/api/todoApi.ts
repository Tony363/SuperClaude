/**
 * Todo API Client
 * Frontend functions for communicating with the backend
 */

import type {
  Todo,
  CreateTodoRequest,
  UpdateTodoRequest,
  ApiResponse
} from '../../shared/types';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';

async function handleResponse<T>(response: Response): Promise<ApiResponse<T>> {
  const data = await response.json();
  return data as ApiResponse<T>;
}

/**
 * Fetch all todos
 */
export async function getTodos(): Promise<ApiResponse<Todo[]>> {
  const response = await fetch(`${API_BASE}/todos`);
  return handleResponse<Todo[]>(response);
}

/**
 * Fetch a single todo by ID
 */
export async function getTodo(id: string): Promise<ApiResponse<Todo>> {
  const response = await fetch(`${API_BASE}/todos/${id}`);
  return handleResponse<Todo>(response);
}

/**
 * Create a new todo
 */
export async function createTodo(data: CreateTodoRequest): Promise<ApiResponse<Todo>> {
  const response = await fetch(`${API_BASE}/todos`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  });
  return handleResponse<Todo>(response);
}

/**
 * Update an existing todo
 */
export async function updateTodo(
  id: string,
  data: UpdateTodoRequest
): Promise<ApiResponse<Todo>> {
  const response = await fetch(`${API_BASE}/todos/${id}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  });
  return handleResponse<Todo>(response);
}

/**
 * Delete a todo
 */
export async function deleteTodo(id: string): Promise<ApiResponse<Todo>> {
  const response = await fetch(`${API_BASE}/todos/${id}`, {
    method: 'DELETE'
  });
  return handleResponse<Todo>(response);
}
