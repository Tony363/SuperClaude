/**
 * TodoItem Component
 * Displays a single todo with toggle and delete functionality
 */

import React, { useState } from 'react';
import type { Todo } from '../../shared/types';
import { updateTodo, deleteTodo } from '../api/todoApi';

interface TodoItemProps {
  todo: Todo;
  onUpdate: (todo: Todo) => void;
  onDelete: (id: string) => void;
}

export function TodoItem({ todo, onUpdate, onDelete }: TodoItemProps): React.ReactElement {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleToggle = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await updateTodo(todo.id, { completed: !todo.completed });
      if (response.success && response.data) {
        onUpdate(response.data);
      } else {
        setError(response.error || 'Failed to update todo');
      }
    } catch (err) {
      setError('Network error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await deleteTodo(todo.id);
      if (response.success) {
        onDelete(todo.id);
      } else {
        setError(response.error || 'Failed to delete todo');
      }
    } catch (err) {
      setError('Network error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="todo-item"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        padding: '12px 16px',
        borderRadius: '8px',
        backgroundColor: '#f8f9fa',
        marginBottom: '8px',
        opacity: isLoading ? 0.7 : 1,
        transition: 'opacity 0.2s'
      }}
    >
      <input
        type="checkbox"
        checked={todo.completed}
        onChange={handleToggle}
        disabled={isLoading}
        aria-label={`Mark "${todo.title}" as ${todo.completed ? 'incomplete' : 'complete'}`}
        style={{
          width: '20px',
          height: '20px',
          cursor: isLoading ? 'wait' : 'pointer'
        }}
      />

      <span
        style={{
          flex: 1,
          textDecoration: todo.completed ? 'line-through' : 'none',
          color: todo.completed ? '#6c757d' : '#212529',
          fontSize: '16px'
        }}
      >
        {todo.title}
      </span>

      <button
        onClick={handleDelete}
        disabled={isLoading}
        aria-label={`Delete "${todo.title}"`}
        style={{
          padding: '6px 12px',
          backgroundColor: '#dc3545',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: isLoading ? 'wait' : 'pointer',
          fontSize: '14px'
        }}
      >
        Delete
      </button>

      {error && (
        <span
          role="alert"
          style={{
            color: '#dc3545',
            fontSize: '12px',
            marginLeft: '8px'
          }}
        >
          {error}
        </span>
      )}
    </div>
  );
}

export default TodoItem;
