// File: ./frontend/src/api.js
// Description: API configuration and interceptors
//
// Auth transport: the browser SPA authenticates via the httpOnly, Secure,
// SameSite=Lax `session_id` cookie the backend sets on login — `withCredentials`
// below is what makes axios send it. We deliberately do NOT mirror the token
// into a JS-readable header: an httpOnly cookie can't be read by injected
// script, so it isn't a viable XSS exfiltration target the way a
// localStorage-backed Authorization header would be. Non-browser API clients
// (scripts, tests, mobile) use the token returned in the /api/login response
// body as a standard `Authorization: Bearer <session_id>` header instead —
// see backend/app/middleware/session_middleware.py.
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

// Request interceptor: for file uploads, drop the default JSON Content-Type
// (and any caller-set boundary-less "multipart/form-data") so the browser
// sets it WITH the multipart boundary — otherwise the server can't parse the
// parts and the upload (avatar, banners, entity images) silently fails.
api.interceptors.request.use(
    config => {
        if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
            if (config.headers && typeof config.headers.delete === 'function') {
                config.headers.delete('Content-Type');
            } else if (config.headers) {
                delete config.headers['Content-Type'];
            }
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