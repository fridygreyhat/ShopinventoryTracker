
/**
 * Authentication related JavaScript functions
 * Enhanced logout functionality with proper error handling
 */

// Global variables for session management
let sessionWarningShown = false;
let logoutInProgress = false;

/**
 * Enhanced logout function with confirmation and proper error handling
 */
function logoutUser() {
    // Prevent multiple logout attempts
    if (logoutInProgress) {
        return;
    }

    // Show confirmation dialog
    if (!confirm('Are you sure you want to log out?')) {
        return;
    }

    logoutInProgress = true;
    
    // Show loading state on logout buttons
    const logoutButtons = document.querySelectorAll('[data-logout], [href*="logout"]');
    logoutButtons.forEach(button => {
        const originalContent = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Logging out...';
        button.disabled = true;
        button.style.pointerEvents = 'none';
    });

    // Show loading notification
    showNotification('Logging out...', 'info');

    // Perform logout request
    fetch('/auth/logout', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    })
    .then(response => {
        if (response.ok) {
            return response.json().catch(() => ({ success: true }));
        } else if (response.redirected) {
            // Handle redirect response
            window.location.href = response.url || '/login';
            return;
        } else {
            throw new Error('HTTP ' + response.status + ': ' + response.statusText);
        }
    })
    .then(data => {
        if (data && data.success) {
            // Clear local storage and session storage
            clearUserData();
            
            // Show success message
            showNotification('Logged out successfully!', 'success');
            
            // Redirect to login page
            setTimeout(() => {
                window.location.href = data.redirect || '/login';
            }, 1000);
        } else {
            throw new Error((data && data.message) || 'Logout failed');
        }
    })
    .catch(error => {
        console.error('Logout error:', error);
        
        // Clear user data anyway
        clearUserData();
        
        // Fallback: direct navigation to logout
        showNotification('Redirecting to logout...', 'warning');
        setTimeout(() => {
            window.location.href = '/auth/logout';
        }, 1000);
    })
    .finally(() => {
        logoutInProgress = false;
    });
}

/**
 * Quick logout function without confirmation
 */
function quickLogout() {
    logoutInProgress = true;
    clearUserData();
    window.location.href = '/logout';
}

/**
 * Clear user data from browser storage
 */
function clearUserData() {
    try {
        // Clear localStorage
        if (typeof(Storage) !== "undefined") {
            const keysToRemove = ['user_theme', 'user_preferences', 'cart_data', 'draft_data'];
            keysToRemove.forEach(key => {
                localStorage.removeItem(key);
            });
        }
        
        // Clear sessionStorage
        sessionStorage.clear();
        
        // Clear any cached form data
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            if (form.reset) {
                form.reset();
            }
        });
    } catch (error) {
        console.warn('Error clearing user data:', error);
    }
}

/**
 * Show notification function
 */
function showNotification(message, type) {
    type = type || 'info';
    
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.auth-notification');
    existingNotifications.forEach(notification => notification.remove());

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed auth-notification`;
    notification.style.cssText = `
        top: 20px; 
        right: 20px; 
        z-index: 9999; 
        min-width: 300px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    notification.innerHTML = 
        '<div class="d-flex align-items-center">' +
            '<i class="fas fa-' + getIconForType(type) + ' me-2"></i>' +
            '<span>' + message + '</span>' +
        '</div>' +
        '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>';
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

/**
 * Get appropriate icon for notification type
 */
function getIconForType(type) {
    const icons = {
        'success': 'check-circle',
        'danger': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle',
        'primary': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

/**
 * Initialize authentication handlers when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing authentication handlers...');
    
    // Add click handlers to logout buttons
    document.querySelectorAll('[data-logout]').forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            logoutUser();
        });
    });
    
    // Add click handlers to quick logout buttons
    document.querySelectorAll('[data-quick-logout]').forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            quickLogout();
        });
    });

    // Handle logout links in navigation
    document.querySelectorAll('a[href*="logout"]').forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            logoutUser();
        });
    });

    // Session timeout management
    initializeSessionTimeout();
});

/**
 * Initialize session timeout warnings
 */
function initializeSessionTimeout() {
    // Set session timeout warning (25 minutes = 1500000ms)
    const sessionTimeoutWarning = setTimeout(() => {
        if (!sessionWarningShown) {
            sessionWarningShown = true;
            const extendSession = confirm(
                'Your session will expire in 5 minutes. Do you want to extend your session?'
            );
            
            if (extendSession) {
                // Make a simple request to extend session
                fetch('/api/auth/profile', {
                    method: 'GET',
                    credentials: 'same-origin'
                }).then(() => {
                    showNotification('Session extended successfully', 'success');
                    sessionWarningShown = false;
                    // Restart the timeout
                    initializeSessionTimeout();
                }).catch(() => {
                    showNotification('Failed to extend session', 'warning');
                });
            }
        }
    }, 1500000); // 25 minutes

    // Force logout after 30 minutes of inactivity
    const forceLogoutTimeout = setTimeout(() => {
        showNotification('Session expired. You will be logged out.', 'warning');
        setTimeout(quickLogout, 3000);
    }, 1800000); // 30 minutes

    // Reset timeouts on user activity
    const resetTimeouts = () => {
        clearTimeout(sessionTimeoutWarning);
        clearTimeout(forceLogoutTimeout);
        sessionWarningShown = false;
        // Restart timeouts
        setTimeout(initializeSessionTimeout, 100);
    };

    // Listen for user activity
    const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
    const throttledReset = throttle(resetTimeouts, 60000); // Throttle to once per minute

    activityEvents.forEach(function(event) {
        document.addEventListener(event, throttledReset, { passive: true });
    });
}

/**
 * Throttle function to limit how often a function can be called
 */
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Handle form submissions with authentication
 */
function handleAuthenticatedForm(form, callback) {
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const submitButton = form.querySelector('button[type="submit"]');
        const originalText = submitButton ? submitButton.innerHTML : '';
        
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
        }
        
        if (callback && typeof callback === 'function') {
            callback(form).finally(() => {
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = originalText;
                }
            });
        }
    });
}

// Export functions for global access
window.logoutUser = logoutUser;
window.quickLogout = quickLogout;
window.showNotification = showNotification;
window.handleAuthenticatedForm = handleAuthenticatedForm;
