import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Inject JWT auth token into Authorization header if present
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('cos_jwt_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response error handler: on 401, clear token and force reload to login screen (unless it's an auth endpoint)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const isAuthRoute = error.config?.url?.includes('/auth/login');
    if (error.response?.status === 401 && !isAuthRoute) {
      console.warn('Authentication token expired or invalid. Redirecting to login.');
      localStorage.removeItem('cos_jwt_token');
      window.location.replace('/');
    }
    return Promise.reject(error);
  }
);
