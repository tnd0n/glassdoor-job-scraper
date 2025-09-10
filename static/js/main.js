// Main JavaScript file for Glassdoor Job Scraper

// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Add smooth scrolling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Utility functions
const Utils = {
    // Format numbers with commas
    formatNumber: function(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    },
    
    // Format currency
    formatCurrency: function(amount) {
        return '$' + this.formatNumber(Math.round(amount));
    },
    
    // Truncate text
    truncateText: function(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substr(0, maxLength) + '...';
    },
    
    // Show loading state
    showLoading: function(element, text = 'Loading...') {
        const spinner = '<div class="spinner-border spinner-border-sm me-2" role="status"></div>';
        element.innerHTML = spinner + text;
        element.disabled = true;
    },
    
    // Hide loading state
    hideLoading: function(element, originalText) {
        element.innerHTML = originalText;
        element.disabled = false;
    },
    
    // Show toast notification
    showToast: function(message, type = 'success') {
        const toastContainer = document.getElementById('toast-container') || this.createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove from DOM after hiding
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    },
    
    // Create toast container if it doesn't exist
    createToastContainer: function() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '1055';
        document.body.appendChild(container);
        return container;
    }
};

// Form validation
const FormValidator = {
    // Validate required fields
    validateRequired: function(form) {
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                this.showFieldError(field, 'This field is required');
                isValid = false;
            } else {
                this.clearFieldError(field);
            }
        });
        
        return isValid;
    },
    
    // Show field error
    showFieldError: function(field, message) {
        field.classList.add('is-invalid');
        
        let feedback = field.nextElementSibling;
        if (!feedback || !feedback.classList.contains('invalid-feedback')) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            field.parentNode.insertBefore(feedback, field.nextSibling);
        }
        
        feedback.textContent = message;
    },
    
    // Clear field error
    clearFieldError: function(field) {
        field.classList.remove('is-invalid');
        
        const feedback = field.nextElementSibling;
        if (feedback && feedback.classList.contains('invalid-feedback')) {
            feedback.remove();
        }
    }
};

// Progress tracking
const ProgressTracker = {
    // Create progress bar
    createProgressBar: function(container, options = {}) {
        const progressDiv = document.createElement('div');
        progressDiv.className = 'progress mb-3';
        
        const progressBar = document.createElement('div');
        progressBar.className = 'progress-bar progress-bar-striped progress-bar-animated';
        progressBar.setAttribute('role', 'progressbar');
        progressBar.style.width = '0%';
        
        progressDiv.appendChild(progressBar);
        container.appendChild(progressDiv);
        
        return {
            element: progressBar,
            update: function(percentage, text = '') {
                this.element.style.width = percentage + '%';
                this.element.textContent = text || percentage + '%';
            },
            complete: function() {
                this.element.classList.remove('progress-bar-animated', 'progress-bar-striped');
                this.element.classList.add('bg-success');
            },
            error: function() {
                this.element.classList.remove('progress-bar-animated', 'progress-bar-striped');
                this.element.classList.add('bg-danger');
            }
        };
    }
};

// Table utilities
const TableUtils = {
    // Add search functionality to table
    addSearch: function(tableId, searchInputId) {
        const table = document.getElementById(tableId);
        const searchInput = document.getElementById(searchInputId);
        
        if (!table || !searchInput) return;
        
        searchInput.addEventListener('keyup', function() {
            const filter = this.value.toLowerCase();
            const rows = table.getElementsByTagName('tr');
            
            for (let i = 1; i < rows.length; i++) {
                const row = rows[i];
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            }
        });
    },
    
    // Add sorting to table
    addSorting: function(tableId) {
        const table = document.getElementById(tableId);
        if (!table) return;
        
        const headers = table.querySelectorAll('th');
        headers.forEach((header, index) => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', function() {
                this.sortTable(table, index);
            }.bind(this));
        });
    },
    
    // Sort table by column
    sortTable: function(table, column) {
        const tbody = table.tBodies[0];
        const rows = Array.from(tbody.rows);
        
        rows.sort((a, b) => {
            const aText = a.cells[column].textContent.trim();
            const bText = b.cells[column].textContent.trim();
            
            // Check if numeric
            if (!isNaN(aText) && !isNaN(bText)) {
                return parseFloat(aText) - parseFloat(bText);
            }
            
            return aText.localeCompare(bText);
        });
        
        rows.forEach(row => tbody.appendChild(row));
    }
};

// Export utilities to global scope
window.Utils = Utils;
window.FormValidator = FormValidator;
window.ProgressTracker = ProgressTracker;
window.TableUtils = TableUtils;