// API client for communicating with FastAPI backend

const API_BASE = 'http://localhost:8000';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(url, config);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Request failed');
    }
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

export const api = {
  // Projects
  getProjects: () => request('/projects'),
  createProject: (data) => request('/projects', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  deleteProject: (id) => request(`/projects/${id}`, { method: 'DELETE' }),

  // Tasks
  getTasks: (params = {}) => {
    const query = new URLSearchParams(params);
    return request(`/tasks?${query}`);
  },
  getTask: (id) => request(`/tasks/${id}`),
  createTask: (data) => request('/tasks', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  createTaskWithScheduling: (data, forceBump = false) => 
    request(`/tasks/with-scheduling?force_bump=${forceBump}`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateTask: (id, data) => request(`/tasks/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  deleteTask: (id) => request(`/tasks/${id}`, { method: 'DELETE' }),
  completeTask: (id) => request(`/tasks/${id}/complete`, { method: 'POST' }),
  getUnscheduledTasks: () => request('/tasks/unscheduled'),

  // Slots
  getSlots: (startDate, endDate) => {
    const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
    return request(`/slots?${params}`);
  },
  deleteSlot: (id) => request(`/slots/${id}`, { method: 'DELETE' }),
  moveSlot: (id, newStart) => request(`/slots/${id}/move`, {
    method: 'PUT',
    body: JSON.stringify({ new_start: newStart }),
  }),
  completeSlot: (id) => request(`/slots/${id}/complete`, { method: 'POST' }),

  // Scheduling
  autoSchedule: () => request('/schedule/auto', { method: 'POST' }),
  scheduleTask: (taskId, forceBump = false) => 
    request(`/schedule/task/${taskId}?force_bump=${forceBump}`, { method: 'POST' }),
  reallocateNow: (data) => request('/schedule/reallocate-now', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  checkFeasibility: (taskId) => request(`/schedule/feasibility/${taskId}`),

  // Time Allocations (Recurring)
  createTimeAllocation: (data) => request('/time-allocations', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  getTimeAllocations: (taskId) => request(`/time-allocations/${taskId}`),

  // Blocked Times
  getBlockedTimes: () => request('/blocked-times'),
  createBlockedTime: (data) => request('/blocked-times', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  deleteBlockedTime: (id) => request(`/blocked-times/${id}`, { method: 'DELETE' }),

  // Settings
  getCalendarSettings: () => request('/settings/calendar'),
  updateCalendarSettings: (data) => request('/settings/calendar', {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),

  // Stats
  getStats: () => request('/stats/overview'),
};
