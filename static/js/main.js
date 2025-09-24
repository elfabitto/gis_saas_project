// Main JavaScript file for GIS SaaS

// Global variables
let currentProject = null;
let uploadedFile = null;

// API Base URL
const API_BASE = '/api';

// Utility functions
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert at the top of main content
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.insertBefore(alertDiv, mainContent.firstChild);
    }
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// API functions
async function apiCall(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    // Merge options
    const finalOptions = { ...defaultOptions, ...options };
    
    // Don't set Content-Type for FormData
    if (finalOptions.body instanceof FormData) {
        delete finalOptions.headers['Content-Type'];
    }
    
    try {
        const response = await fetch(url, finalOptions);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || errorData.error || `HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Project functions
async function createProject(name, description) {
    return await apiCall('/projects/', {
        method: 'POST',
        body: JSON.stringify({
            name: name,
            description: description
        })
    });
}

async function getProjects(limit = null) {
    const params = limit ? `?limit=${limit}` : '';
    return await apiCall(`/projects/${params}`);
}

async function getProject(projectId) {
    return await apiCall(`/projects/${projectId}/`);
}

// File upload functions
async function uploadFile(projectId, file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_id', projectId);
    
    return await apiCall('/upload/', {
        method: 'POST',
        body: formData
    });
}

// Layout functions
async function getLayouts(type = null) {
    const params = type ? `?type=${type}` : '';
    return await apiCall(`/layouts/${params}`);
}

// Configuration functions
async function saveMapConfiguration(config) {
    return await apiCall('/configurations/', {
        method: 'POST',
        body: JSON.stringify(config)
    });
}

// Map generation functions
async function generateMap(projectId, outputFormat) {
    return await apiCall('/generated-maps/generate/', {
        method: 'POST',
        body: JSON.stringify({
            project_id: projectId,
            output_format: outputFormat
        })
    });
}

async function generateModernMap(projectId, outputFormat) {
    return await apiCall('/generated-maps/generate_modern/', {
        method: 'POST',
        body: JSON.stringify({
            project_id: projectId,
            output_format: outputFormat
        })
    });
}

async function getGeneratedMaps(projectId = null) {
    const params = projectId ? `?project=${projectId}` : '';
    return await apiCall(`/generated-maps/${params}`);
}

// File drag and drop functionality
function initializeFileUpload(uploadAreaId, fileInputId, onFileSelect) {
    const uploadArea = document.getElementById(uploadAreaId);
    const fileInput = document.getElementById(fileInputId);
    
    if (!uploadArea || !fileInput) return;
    
    // Click to select file
    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });
    
    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            onFileSelect(e.target.files[0]);
        }
    });
    
    // Drag and drop events
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            onFileSelect(files[0]);
        }
    });
}

// Progress bar functions
function showProgress(progressId, statusId) {
    const progressDiv = document.getElementById(progressId);
    if (progressDiv) {
        progressDiv.style.display = 'block';
    }
}

function updateProgress(progressId, percentage, statusText = '') {
    const progressBar = document.querySelector(`#${progressId} .progress-bar`);
    const statusElement = document.getElementById('upload-status');
    
    if (progressBar) {
        progressBar.style.width = `${percentage}%`;
        progressBar.setAttribute('aria-valuenow', percentage);
    }
    
    if (statusElement && statusText) {
        statusElement.textContent = statusText;
    }
}

function hideProgress(progressId) {
    const progressDiv = document.getElementById(progressId);
    if (progressDiv) {
        progressDiv.style.display = 'none';
    }
}

// Form validation
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

// Loading states
function setLoading(elementId, isLoading) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    if (isLoading) {
        element.disabled = true;
        const originalText = element.textContent;
        element.dataset.originalText = originalText;
        element.innerHTML = '<span class="loading me-2"></span>Carregando...';
    } else {
        element.disabled = false;
        element.textContent = element.dataset.originalText || 'Concluído';
    }
}

// Initialize common functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Add smooth scrolling to anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
});

// Export functions for use in other scripts
window.GISSaaS = {
    showAlert,
    formatFileSize,
    formatDate,
    apiCall,
    createProject,
    getProjects,
    getProject,
    uploadFile,
    getLayouts,
    saveMapConfiguration,
    generateMap,
    generateModernMap,
    getGeneratedMaps,
    initializeFileUpload,
    showProgress,
    updateProgress,
    hideProgress,
    validateForm,
    setLoading
};
