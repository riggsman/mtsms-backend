// API utility with automatic token refresh
let isRefreshing = false;
let refreshPromise = null;

const API_BASE_URL = 'http://localhost:8000';

/**
 * Get authentication headers
 */
export const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  const headers = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
};

/**
 * Refresh access token using refresh token
 */
const refreshToken = async () => {
  const refreshTokenValue = localStorage.getItem('refreshToken');
  if (!refreshTokenValue) {
    throw new Error('No refresh token available');
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/v1/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        refresh_token: refreshTokenValue,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Failed to refresh token');
    }

    const data = await response.json();
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('refreshToken', data.refresh_token);
    return data.access_token;
  } catch (error) {
    // Clear tokens on refresh failure
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
    localStorage.removeItem('tenantName');
    throw error;
  }
};

/**
 * Handle 401 response - refresh token or logout
 */
const handle401Response = async (response, originalRequest) => {
  // Check if user is active by trying to refresh
  const refreshTokenValue = localStorage.getItem('refreshToken');
  
  if (!refreshTokenValue) {
    // No refresh token, logout
    logout();
    return null;
  }

  // If already refreshing, wait for that promise
  if (isRefreshing) {
    try {
      await refreshPromise;
      // Retry original request with new token
      return fetch(originalRequest.url, {
        ...originalRequest,
        headers: {
          ...originalRequest.headers,
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });
    } catch (error) {
      logout();
      return null;
    }
  }

  // Start refresh process
  isRefreshing = true;
  refreshPromise = refreshToken();

  try {
    await refreshPromise;
    // Retry original request with new token
    return fetch(originalRequest.url, {
      ...originalRequest,
      headers: {
        ...originalRequest.headers,
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
    });
  } catch (error) {
    // Refresh failed, logout
    logout();
    return null;
  } finally {
    isRefreshing = false;
    refreshPromise = null;
  }
};

/**
 * Logout user and redirect to login
 */
export const logout = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('user');
  localStorage.removeItem('tenantName');
  window.location.href = '/login';
};

/**
 * Enhanced fetch with automatic token refresh
 */
export const apiRequest = async (url, options = {}) => {
  // Check if token is missing but includeAuth is true
  const token = localStorage.getItem('token');
  const refreshTokenValue = localStorage.getItem('refreshToken');
  const includeAuth = options.includeAuth !== false; // Default to true unless explicitly false

  // If token is missing but we have refresh token and auth is required, try to refresh first
  if (!token && refreshTokenValue && includeAuth) {
    try {
      await refreshToken();
    } catch (error) {
      // Refresh failed, logout
      logout();
      throw new Error('Authentication failed: Unable to refresh token');
    }
  }

  const headers = {
    ...getAuthHeaders(),
    ...options.headers,
  };

  const requestOptions = {
    ...options,
    headers,
  };

  // Remove includeAuth from options as it's not a fetch option
  delete requestOptions.includeAuth;

  // Add full URL if relative
  const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;

  let response = await fetch(fullUrl, requestOptions);

  // Handle 401 Unauthorized - token expired or missing
  if (response.status === 401) {
    const errorData = await response.json().catch(() => ({}));
    const errorMessage = errorData.detail || 'Unauthorized';

    // Check if error indicates user is not active
    if (errorMessage.includes('not active') || errorMessage.includes('Token expired and user is not active')) {
      // User is not active, logout immediately
      logout();
      throw new Error('User account is not active');
    }

    // Check if token is missing but we have refresh token
    if (!token && refreshTokenValue) {
      try {
        await refreshToken();
        // Retry request with new token
        requestOptions.headers = {
          ...requestOptions.headers,
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        };
        response = await fetch(fullUrl, requestOptions);
        
        // If still 401, logout
        if (response.status === 401) {
          logout();
          throw new Error('Authentication failed after token refresh');
        }
      } catch (error) {
        // Refresh failed, logout
        logout();
        throw error;
      }
    } else {
      // Try to refresh token if we have one
      const retryResponse = await handle401Response(response, {
        url: fullUrl,
        ...requestOptions,
      });

      if (retryResponse) {
        response = retryResponse;
      } else {
        // Refresh failed or user not active
        logout();
        throw new Error('Authentication failed');
      }
    }
  }

  return response;
};

/**
 * Convenience methods for common HTTP verbs
 * @param {string} url - API endpoint URL
 * @param {object} options - Request options (includeAuth defaults to true)
 * @param {boolean} options.includeAuth - Whether to include authentication (default: true)
 */
export const api = {
  get: (url, options = {}) => apiRequest(url, { ...options, method: 'GET' }),
  post: (url, data, options = {}) =>
    apiRequest(url, {
      ...options,
      method: 'POST',
      body: JSON.stringify(data),
    }),
  put: (url, data, options = {}) =>
    apiRequest(url, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  patch: (url, data, options = {}) =>
    apiRequest(url, {
      ...options,
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  delete: (url, options = {}) => apiRequest(url, { ...options, method: 'DELETE' }),
};
