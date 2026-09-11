// File: ./frontend/src/index.js

import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import './styles/theme.css';
import App from './App';

// One query cache for the whole app (see utils/queries.js). Requests for the
// same key are de-duplicated and kept fresh for a short window, so the many
// pages that read the same lists share one round-trip instead of each firing
// their own.
const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
            retry: 1,
        },
    },
});

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </React.StrictMode>,
);
