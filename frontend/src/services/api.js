import axios from 'axios';

// In dev always use /api so Vite proxy hits backend (avoids CORS). Production uses VITE_API_BASE_URL.
const API_BASE_URL = import.meta.env.DEV ? '/api' : (import.meta.env.VITE_API_BASE_URL || '/api');

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add JWT to all requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle errors globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
    }
    return Promise.reject(error);
  }
);

// ============================================================================
// AUTH SERVICES
// ============================================================================

export const authService = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data)
};

// ============================================================================
// USER SERVICES
// ============================================================================

export const userService = {
  getProfile: () => api.get('/users/profile'),
  updateProfile: (data) => api.patch('/users/profile', data),
  getGameStats: () => api.get('/gamification/stats')
};

// ============================================================================
// GOAL SERVICES
// ============================================================================

export const goalService = {
  create: (data) => api.post('/goals', data),
  getAll: () => api.get('/goals'),
  contribute: (goalId, amount) => api.post(`/goals/${goalId}/contribute`, { amount })
};

// ============================================================================
// QUEST SERVICES
// ============================================================================

export const questService = {
  getAvailable: () => api.get('/quests/available'),
  getActive: () => api.get('/quests/active'),
  accept: (questId) => api.post(`/quests/${questId}/accept`),
  complete: (userQuestId) => api.post(`/quests/${userQuestId}/complete`)
};

// ============================================================================
// GAMIFICATION SERVICES
// ============================================================================

export const gamificationService = {
  getLeaderboard: (limit = 100) => api.get(`/gamification/leaderboard?limit=${limit}`),
  placePopCityItem: () => api.post('/gamification/pop-city-place'),
};

// ============================================================================
// AI SERVICES
// ============================================================================

export const aiService = {
  chat: (message) => api.post('/ai/chat', { message })
};

// ============================================================================
// VETO REQUESTS (cross-user: Anna creates, Suhani sees)
// ============================================================================

export const vetoService = {
  getAll: () => api.get('/veto-requests'),
  create: (data) => api.post('/veto-requests', data),
  vote: (requestId, vote) => api.post(`/veto-requests/${requestId}/vote`, { vote }),
};

// ============================================================================
// BANKING SERVICES
// ============================================================================

export const bankingService = {
  getCustomers: () => api.get('/banking/customers'),
  getAccounts: (customerId) => api.get(`/banking/accounts/${customerId}`),
  getTransactions: (accountId) => api.get(`/banking/transactions/${accountId}`)
};

export default api;
