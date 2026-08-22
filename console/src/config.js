// Centralized API configuration for local dev and production hosting
export const API_BASE = window.location.port === '5173' ? 'http://127.0.0.1:8000' : '';
