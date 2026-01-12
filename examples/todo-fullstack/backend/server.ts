/**
 * Node.js API Server for Todo Items
 * Express-based REST API with in-memory storage
 */

import express, { Request, Response, NextFunction } from 'express';
import cors from 'cors';
import { randomUUID } from 'crypto';
import type { Todo, CreateTodoRequest, UpdateTodoRequest, ApiResponse } from '../shared/types';

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// In-memory storage (replace with database in production)
const todos: Map<string, Todo> = new Map();

// Request validation middleware
function validateCreateTodo(req: Request, res: Response, next: NextFunction): void {
  const { title } = req.body as CreateTodoRequest;
  if (!title || typeof title !== 'string' || title.trim().length === 0) {
    res.status(400).json({
      success: false,
      error: 'Title is required and must be a non-empty string'
    } satisfies ApiResponse<never>);
    return;
  }
  next();
}

// Routes

// GET /api/todos - List all todos
app.get('/api/todos', (_req: Request, res: Response) => {
  const todoList = Array.from(todos.values()).sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  );
  res.json({
    success: true,
    data: todoList
  } satisfies ApiResponse<Todo[]>);
});

// GET /api/todos/:id - Get single todo
app.get('/api/todos/:id', (req: Request, res: Response) => {
  const todo = todos.get(req.params.id);
  if (!todo) {
    res.status(404).json({
      success: false,
      error: 'Todo not found'
    } satisfies ApiResponse<never>);
    return;
  }
  res.json({
    success: true,
    data: todo
  } satisfies ApiResponse<Todo>);
});

// POST /api/todos - Create new todo
app.post('/api/todos', validateCreateTodo, (req: Request, res: Response) => {
  const { title } = req.body as CreateTodoRequest;
  const now = new Date().toISOString();

  const todo: Todo = {
    id: randomUUID(),
    title: title.trim(),
    completed: false,
    createdAt: now,
    updatedAt: now
  };

  todos.set(todo.id, todo);

  res.status(201).json({
    success: true,
    data: todo
  } satisfies ApiResponse<Todo>);
});

// PATCH /api/todos/:id - Update todo
app.patch('/api/todos/:id', (req: Request, res: Response) => {
  const todo = todos.get(req.params.id);
  if (!todo) {
    res.status(404).json({
      success: false,
      error: 'Todo not found'
    } satisfies ApiResponse<never>);
    return;
  }

  const updates = req.body as UpdateTodoRequest;
  const updatedTodo: Todo = {
    ...todo,
    ...(updates.title !== undefined && { title: updates.title.trim() }),
    ...(updates.completed !== undefined && { completed: updates.completed }),
    updatedAt: new Date().toISOString()
  };

  todos.set(todo.id, updatedTodo);

  res.json({
    success: true,
    data: updatedTodo
  } satisfies ApiResponse<Todo>);
});

// DELETE /api/todos/:id - Delete todo
app.delete('/api/todos/:id', (req: Request, res: Response) => {
  const todo = todos.get(req.params.id);
  if (!todo) {
    res.status(404).json({
      success: false,
      error: 'Todo not found'
    } satisfies ApiResponse<never>);
    return;
  }

  todos.delete(req.params.id);

  res.json({
    success: true,
    data: todo
  } satisfies ApiResponse<Todo>);
});

// Error handling middleware
app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
  console.error('Server error:', err);
  res.status(500).json({
    success: false,
    error: 'Internal server error'
  } satisfies ApiResponse<never>);
});

// Start server
app.listen(PORT, () => {
  console.log(`Todo API server running on http://localhost:${PORT}`);
});

export { app };
