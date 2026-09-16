// ============================================
// BACKEND API INTEGRATION
// ============================================

// Flask serves this frontend itself, so the API normally lives on the same
// origin (localhost, 127.0.0.1, a LAN IP or a deployed host all work).
// When the frontend is hosted separately from the API, point this elsewhere
// with `window.SMART_CAMPUS_API_BASE = 'https://api.example.com/api'`.
const API_BASE_URL = window.SMART_CAMPUS_API_BASE ||
    (window.location.origin.startsWith('http')
        ? `${window.location.origin}/api`
        : 'http://localhost:5000/api');

// API Helper
async function apiRequest(endpoint, method = 'GET', data = null) {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
    };

    // Add token if available
    const token = localStorage.getItem('token');
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const options = {
        method,
        headers,
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(url, options);
        let result;
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            result = await response.json();
        } else {
            const text = await response.text();
            result = { error: text || `HTTP ${response.status}: ${response.statusText}` };
        }

        if (!response.ok) {
            throw new Error(result.error || `Request failed with status ${response.status}`);
        }

        return result;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Authentication Functions
async function login(email, password) {
    try {
        const result = await apiRequest('/auth/login', 'POST', { email, password });
        if (result.token) {
            localStorage.setItem('token', result.token);
            localStorage.setItem('user', JSON.stringify(result.user));
            showToast('✅ Login successful!', 'success');
            return result;
        }
        return null;
    } catch (error) {
        showToast(error.message, 'error');
        return null;
    }
}

async function signup(userData) {
    try {
        const result = await apiRequest('/auth/signup', 'POST', userData);
        if (result.token) {
            localStorage.setItem('token', result.token);
            localStorage.setItem('user', JSON.stringify(result.user));
            showToast('✅ Account created successfully!', 'success');
            return result;
        }
        return null;
    } catch (error) {
        showToast(error.message, 'error');
        return null;
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    showToast('Logged out successfully', 'info');
    setTimeout(() => {
        window.location.href = 'index.html';
    }, 500);
}

function getCurrentUser() {
    try {
        const user = localStorage.getItem('user');
        return user ? JSON.parse(user) : null;
    } catch (e) {
        console.error('Error parsing current user from localStorage:', e);
        return null;
    }
}

function isLoggedIn() {
    return !!localStorage.getItem('token');
}

function isAdmin() {
    const user = getCurrentUser();
    return !!user && user.role === 'admin';
}

// Escape HTML to avoid breaking markup / XSS when rendering user content
function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Facility Functions
async function getFacilities() {
    try {
        const result = await apiRequest('/facilities');
        return result.facilities || [];
    } catch (error) {
        console.error('Error fetching facilities:', error);
        return [];
    }
}

async function createFacility(data) {
    const result = await apiRequest('/facilities', 'POST', data);
    showToast('✅ Facility created successfully!', 'success');
    return result;
}

async function updateFacility(facilityId, data) {
    const result = await apiRequest(`/facilities/${facilityId}`, 'PUT', data);
    showToast('✅ Facility updated successfully!', 'success');
    return result;
}

async function updateFacilityStatus(facilityId, status) {
    const result = await apiRequest(`/facilities/${facilityId}/status`, 'PATCH', { status });
    showToast('✅ Facility status updated!', 'success');
    return result;
}

async function deleteFacility(facilityId) {
    const result = await apiRequest(`/facilities/${facilityId}`, 'DELETE');
    showToast('✅ Facility deleted', 'success');
    return result;
}

// File Upload Function
async function uploadFile(file) {
    const url = `${API_BASE_URL}/uploads`;
    const formData = new FormData();
    formData.append('file', file);

    const headers = {};
    const token = localStorage.getItem('token');
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
        method: 'POST',
        headers,
        body: formData
    });

    let result;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
        result = await response.json();
    } else {
        const text = await response.text();
        result = { error: text || `HTTP ${response.status}: ${response.statusText}` };
    }

    if (!response.ok) {
        throw new Error(result.error || 'File upload failed');
    }

    return result;
}

// Announcement Functions
async function getAnnouncements(params = {}) {
    try {
        const query = new URLSearchParams();
        if (params.page) query.set('page', params.page);
        if (params.limit) query.set('limit', params.limit);
        if (params.priority && params.priority !== 'all') query.set('priority', params.priority);
        if (params.category && params.category !== 'all') query.set('category', params.category);
        if (params.search) query.set('search', params.search);

        const qs = query.toString() ? `?${query.toString()}` : '';
        const result = await apiRequest(`/announcements${qs}`);
        return result;
    } catch (error) {
        console.error('Error fetching announcements:', error);
        return { announcements: [], total: 0, page: 1, pages: 1 };
    }
}

async function getRecentAnnouncements(limit = 5) {
    try {
        const result = await apiRequest(`/announcements/recent?limit=${limit}`);
        return result.announcements || [];
    } catch (error) {
        console.error('Error fetching recent announcements:', error);
        return [];
    }
}

async function createAnnouncement(data) {
    const result = await apiRequest('/announcements', 'POST', data);
    showToast('✅ Announcement published!', 'success');
    return result;
}

async function deleteAnnouncement(announcementId) {
    const result = await apiRequest(`/announcements/${announcementId}`, 'DELETE');
    showToast('✅ Announcement deleted', 'success');
    return result;
}

// Issue Functions
async function reportIssue(issueData) {
    return await apiRequest('/issues', 'POST', issueData);
}

async function getIssues(params = {}) {
    try {
        const query = new URLSearchParams();
        if (params.page) query.set('page', params.page);
        if (params.limit) query.set('limit', params.limit);
        if (params.status && params.status !== 'all') query.set('status', params.status);
        if (params.facility && params.facility !== 'all') query.set('facility', params.facility);
        if (params.search) query.set('search', params.search);

        const qs = query.toString() ? `?${query.toString()}` : '';
        const result = await apiRequest(`/issues${qs}`);
        return result;
    } catch (error) {
        console.error('Error fetching issues:', error);
        return { issues: [], total: 0, page: 1, pages: 1 };
    }
}

async function getIssueStats() {
    try {
        const result = await apiRequest('/issues/stats');
        return result.stats || null;
    } catch (error) {
        console.error('Error fetching issue stats:', error);
        return null;
    }
}

async function trackIssues(email) {
    try {
        const result = await apiRequest(`/issues/track?email=${encodeURIComponent(email)}`);
        return result.issues || [];
    } catch (error) {
        console.error('Error tracking issues:', error);
        throw error;
    }
}

async function updateIssueStatus(issueId, status) {
    const result = await apiRequest(`/issues/${issueId}/status`, 'PATCH', { status });
    showToast('✅ Issue status updated!', 'success');
    return result;
}

// Admin User Management Functions
async function getAdminUsers(params = {}) {
    try {
        const query = new URLSearchParams();
        if (params.page) query.set('page', params.page);
        if (params.limit) query.set('limit', params.limit);
        if (params.role && params.role !== 'all') query.set('role', params.role);
        if (params.status && params.status !== 'all') query.set('status', params.status);
        if (params.search) query.set('search', params.search);

        const qs = query.toString() ? `?${query.toString()}` : '';
        return await apiRequest(`/admin/users${qs}`);
    } catch (error) {
        console.error('Error fetching admin users:', error);
        throw error;
    }
}

async function updateUserRole(userId, role) {
    const result = await apiRequest(`/admin/users/${userId}/role`, 'PATCH', { role });
    showToast(`✅ ${result.message || 'User role updated'}`, 'success');
    return result;
}

async function updateUserStatus(userId, isActive) {
    const result = await apiRequest(`/admin/users/${userId}/status`, 'PATCH', { is_active: isActive });
    showToast(`✅ ${result.message || 'User status updated'}`, 'success');
    return result;
}

async function deleteUser(userId) {
    const result = await apiRequest(`/admin/users/${userId}`, 'DELETE');
    showToast(`✅ ${result.message || 'User deleted'}`, 'success');
    return result;
}

// Dashboard Functions
async function getDashboardStats() {
    try {
        const result = await apiRequest('/dashboard/stats');
        return result.stats || null;
    } catch (error) {
        console.error('Error fetching dashboard stats:', error);
        return null;
    }
}

// Profile Functions
async function getUserProfile() {
    try {
        const result = await apiRequest('/auth/profile');
        return result.user || null;
    } catch (error) {
        console.error('Error fetching profile:', error);
        return null;
    }
}

async function updateUserProfile(data) {
    const result = await apiRequest('/auth/profile', 'PUT', data);
    showToast('✅ Profile updated successfully!', 'success');
    return result;
}

// Toast Notification System
function showToast(message, type = 'info', duration = 3000) {
    // Remove existing toasts if too many
    const existingToasts = document.querySelectorAll('.toast');
    if (existingToasts.length >= 3) {
        existingToasts[0].remove();
    }

    // Create container if it doesn't exist
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    // Create toast
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icons = {
        success: '✅',
        error: '❌',
        info: 'ℹ️',
        warning: '⚠️'
    };

    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    container.appendChild(toast);

    // Auto remove after duration
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.animation = 'slideInRight 0.4s ease reverse';
            setTimeout(() => toast.remove(), 400);
        }
    }, duration);
}

// Update Navigation
function updateNavigation() {
    const user = getCurrentUser();
    const nav = document.querySelector('header nav ul');
    if (!nav) return;

    // Highlight the link for the page we are currently on
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';

    const link = (href, label) => {
        const active = (href === currentPage) ? ' class="active"' : '';
        return `<li><a href="${href}"${active}>${label}</a></li>`;
    };

    if (user) {
        const isAdmin = user.role === 'admin';
        nav.innerHTML = [
            link('index.html', 'Home'),
            link('facilities.html', 'Facilities'),
            link('announcements.html', 'Announcements'),
            link('my-reports.html', 'My Reports'),
            link('dashboard.html', 'Dashboard'),
            isAdmin ? link('admin.html', 'Admin') : '',
            link('profile.html', 'Profile'),
            '<li><a href="#" onclick="logout()">Logout</a></li>'
        ].join('');
    } else {
        nav.innerHTML = [
            link('index.html', 'Home'),
            link('facilities.html', 'Facilities'),
            link('announcements.html', 'Announcements'),
            link('login.html', 'Login'),
            link('signup.html', 'Sign Up')
        ].join('');
    }
}

// Form Validation
function validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function validatePassword(password) {
    return password.length >= 6;
}

// Make functions globally available
window.login = login;
window.signup = signup;
window.logout = logout;
window.getCurrentUser = getCurrentUser;
window.isLoggedIn = isLoggedIn;
window.isAdmin = isAdmin;
window.escapeHtml = escapeHtml;
window.getFacilities = getFacilities;
window.createFacility = createFacility;
window.updateFacility = updateFacility;
window.updateFacilityStatus = updateFacilityStatus;
window.deleteFacility = deleteFacility;
window.getAnnouncements = getAnnouncements;
window.getRecentAnnouncements = getRecentAnnouncements;
window.createAnnouncement = createAnnouncement;
window.deleteAnnouncement = deleteAnnouncement;
window.reportIssue = reportIssue;
window.getIssues = getIssues;
window.getIssueStats = getIssueStats;
window.trackIssues = trackIssues;
window.updateIssueStatus = updateIssueStatus;
window.getDashboardStats = getDashboardStats;
window.getUserProfile = getUserProfile;
window.updateUserProfile = updateUserProfile;
window.showToast = showToast;
window.updateNavigation = updateNavigation;
window.uploadFile = uploadFile;
window.getAdminUsers = getAdminUsers;
window.updateUserRole = updateUserRole;
window.updateUserStatus = updateUserStatus;
window.deleteUser = deleteUser;
window.validateEmail = validateEmail;
window.validatePassword = validatePassword;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function () {
    updateNavigation();

    // Register Service Worker for PWA & offline support
    if ('serviceWorker' in navigator && window.location.protocol.startsWith('http')) {
        navigator.serviceWorker.register('/sw.js')
            .then(reg => console.log('📱 PWA Service Worker active:', reg.scope))
            .catch(err => console.warn('PWA Service Worker registration skipped:', err));
    }
});
