import React from 'react';
import { PaginatedList } from './PaginatedList';
import type { FetchParams, FetchResult } from './types';
import './PaginatedList.css';

// Example item type
interface User {
  id: number;
  name: string;
  email: string;
  role: string;
  status: 'active' | 'inactive';
}

// Mock data generator
const generateMockUsers = (count: number): User[] => {
  const roles = ['Admin', 'Developer', 'Designer', 'Manager', 'Analyst'];
  const statuses: ('active' | 'inactive')[] = ['active', 'inactive'];

  return Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    name: `User ${i + 1}`,
    email: `user${i + 1}@example.com`,
    role: roles[i % roles.length],
    status: statuses[i % 3 === 0 ? 1 : 0],
  }));
};

// Simulated API with 150 total users
const MOCK_USERS = generateMockUsers(150);

// Mock fetch function that simulates API call with delay
const fetchUsers = async (params: FetchParams): Promise<FetchResult<User>> => {
  // Simulate network delay
  await new Promise((resolve) => setTimeout(resolve, 800));

  // Uncomment to test error state:
  // if (Math.random() > 0.7) {
  //   throw new Error('Failed to connect to server. Please try again.');
  // }

  const { page, pageSize } = params;
  const startIndex = (page - 1) * pageSize;
  const items = MOCK_USERS.slice(startIndex, startIndex + pageSize);

  return {
    items,
    totalItems: MOCK_USERS.length,
    currentPage: page,
    pageSize,
  };
};

// Custom item renderer
const renderUserItem = (user: User): React.ReactNode => (
  <div className="user-card">
    <div className="user-card__header">
      <span className="user-card__name">{user.name}</span>
      <span
        className={`user-card__status user-card__status--${user.status}`}
      >
        {user.status}
      </span>
    </div>
    <div className="user-card__details">
      <span className="user-card__email">{user.email}</span>
      <span className="user-card__role">{user.role}</span>
    </div>
  </div>
);

// Main example component
export const PaginatedListExample: React.FC = () => {
  return (
    <div className="example-container">
      <header className="example-header">
        <h1>PaginatedList Component Demo</h1>
        <p>A fully accessible, TypeScript-powered pagination component</p>
      </header>

      <PaginatedList<User>
        fetchData={fetchUsers}
        renderItem={renderUserItem}
        keyExtractor={(user) => user.id}
        paginationConfig={{
          initialPage: 1,
          pageSize: 10,
          pageSizeOptions: [5, 10, 25, 50],
          showPageSizeSelector: true,
          showPageNumbers: true,
          maxPageButtons: 7,
        }}
        ariaLabel="User directory"
        className="users-list"
      />

      <style>{`
        .example-container {
          max-width: 900px;
          margin: 2rem auto;
          padding: 0 1rem;
        }

        .example-header {
          text-align: center;
          margin-bottom: 2rem;
        }

        .example-header h1 {
          margin: 0 0 0.5rem 0;
          color: #1e293b;
          font-size: 1.5rem;
        }

        .example-header p {
          margin: 0;
          color: #64748b;
        }

        .user-card {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .user-card__header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .user-card__name {
          font-weight: 600;
          color: #1e293b;
        }

        .user-card__status {
          padding: 0.25rem 0.75rem;
          border-radius: 9999px;
          font-size: 0.75rem;
          font-weight: 500;
          text-transform: uppercase;
        }

        .user-card__status--active {
          background: #dcfce7;
          color: #166534;
        }

        .user-card__status--inactive {
          background: #fef2f2;
          color: #dc2626;
        }

        .user-card__details {
          display: flex;
          gap: 1rem;
          font-size: 0.875rem;
          color: #64748b;
        }

        .user-card__role {
          padding: 0.125rem 0.5rem;
          background: #f1f5f9;
          border-radius: 4px;
          font-size: 0.75rem;
        }
      `}</style>
    </div>
  );
};

export default PaginatedListExample;
