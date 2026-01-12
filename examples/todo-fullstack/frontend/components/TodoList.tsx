/**
 * TodoList Component
 * Main container for todo functionality
 */

import React, { useState, useEffect } from 'react';
import type { Todo } from '../../shared/types';
import { getTodos, createTodo } from '../api/todoApi';
import { TodoItem } from './TodoItem';

export function TodoList(): React.ReactElement {
  const [todos, setTodos] = useState<Todo[]>([]);
  const [newTitle, setNewTitle] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadTodos();
  }, []);

  const loadTodos = async () => {
    setIsLoading(true);
    try {
      const response = await getTodos();
      if (response.success && response.data) {
        setTodos(response.data);
      } else {
        setError(response.error || 'Failed to load todos');
      }
    } catch (err) {
      setError('Network error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    setError(null);
    try {
      const response = await createTodo({ title: newTitle.trim() });
      if (response.success && response.data) {
        setTodos([response.data, ...todos]);
        setNewTitle('');
      } else {
        setError(response.error || 'Failed to create todo');
      }
    } catch (err) {
      setError('Network error');
    }
  };

  const handleUpdate = (updatedTodo: Todo) => {
    setTodos(todos.map(t => (t.id === updatedTodo.id ? updatedTodo : t)));
  };

  const handleDelete = (id: string) => {
    setTodos(todos.filter(t => t.id !== id));
  };

  return (
    <div
      className="todo-list"
      style={{
        maxWidth: '600px',
        margin: '0 auto',
        padding: '24px',
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}
    >
      <h1 style={{ marginBottom: '24px', color: '#212529' }}>Todo List</h1>

      <form
        onSubmit={handleSubmit}
        style={{
          display: 'flex',
          gap: '12px',
          marginBottom: '24px'
        }}
      >
        <input
          type="text"
          value={newTitle}
          onChange={e => setNewTitle(e.target.value)}
          placeholder="What needs to be done?"
          aria-label="New todo title"
          style={{
            flex: 1,
            padding: '12px 16px',
            fontSize: '16px',
            border: '1px solid #ced4da',
            borderRadius: '8px'
          }}
        />
        <button
          type="submit"
          disabled={!newTitle.trim()}
          style={{
            padding: '12px 24px',
            backgroundColor: '#0d6efd',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            fontSize: '16px',
            cursor: newTitle.trim() ? 'pointer' : 'not-allowed',
            opacity: newTitle.trim() ? 1 : 0.6
          }}
        >
          Add
        </button>
      </form>

      {error && (
        <div
          role="alert"
          style={{
            padding: '12px 16px',
            backgroundColor: '#f8d7da',
            color: '#842029',
            borderRadius: '8px',
            marginBottom: '16px'
          }}
        >
          {error}
        </div>
      )}

      {isLoading ? (
        <p style={{ textAlign: 'center', color: '#6c757d' }}>Loading...</p>
      ) : todos.length === 0 ? (
        <p style={{ textAlign: 'center', color: '#6c757d' }}>
          No todos yet. Add one above!
        </p>
      ) : (
        <div>
          {todos.map(todo => (
            <TodoItem
              key={todo.id}
              todo={todo}
              onUpdate={handleUpdate}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      <p style={{ marginTop: '24px', color: '#6c757d', fontSize: '14px' }}>
        {todos.filter(t => t.completed).length} of {todos.length} completed
      </p>
    </div>
  );
}

export default TodoList;
