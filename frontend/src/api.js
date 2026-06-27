// File: ./frontend/src/api.js
// Description: API configuration and interceptors
import axios from 'axios';

const api = axios.create({
    // Relative by default so dev requests are same-origin and proxied to the
    // backend via package.json "proxy" (keeps the session cookie first-party).
    // In production set REACT_APP_API_URL to the backend's absolute URL.
    baseURL: process.env.REACT_APP_API_URL || '',
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json'
    }
});

// Request interceptor: forward the session_id cookie as a header too (the
// backend accepts either). Note: the cookie is httpOnly, so document.cookie
// won't actually expose it — this is a best-effort fallback.
api.interceptors.request.use(
    config => {
        const cookies = document.cookie.split(';');
        const sessionCookie = cookies.find(cookie => cookie.trim().startsWith('session_id='));
        if (sessionCookie) {
            const sessionId = sessionCookie.split('=')[1];
            config.headers['session_id'] = sessionId;
        }
        return config;
    },
    error => {
        return Promise.reject(error);
    }
);

// Response interceptor
api.interceptors.response.use(
    response => response,
    error => {
        if (error.response?.status === 401) {
            // Clear cached auth flag. We intentionally do NOT hard-redirect to
            // /login here: route guards are currently disabled in App.js, and a
            // forced redirect on any background 401 caused navigation loops.
            localStorage.removeItem('isLoggedIn');
        }
        return Promise.reject(error);
    }
);

export default api;