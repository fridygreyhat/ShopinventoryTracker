
/**
 * Authentication related JavaScript functions
 */

// Enhanced logout function
function logoutUser() {
    // Show confirmation dialog
    if (confirm('Are you sure you want to log out?')) {
        // Show loading state
        const logoutButton = document.querySelector('[data-logout]');
        if (logoutButton) {
            logoutButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Logging out...';
            logoutButton.disabled = true;
        }
        
        // Make AJAX request to logout
        fetch('/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success message
                showNotification('Logged out successfully!', 'success');
                
                // Clear any cached data
                if (typeof(Storage) !== "undefined") {
                    localStorage.removeItem('user_theme');
                    sessionStorage.clear();
                }
                
                // Redirect after a short delay
                setTimeout(() => {
                    window.location.href = data.redirect || '/login';
                }, 1000);
            } else {
                throw new Error(data.message || 'Logout failed');
            }
        })
        .catch(error => {
            console.error('Logout error:', error);
            // Fallback - redirect to logout URL directly
            window.location.href = '/logout';
        });
    }
}

// Quick logout function (no confirmation)
function quickLogout() {
    window.location.href = '/logout';
}

// Show notification function
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 3000);
}

// Initialize logout handlers when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add click handlers to logout buttons
    document.querySelectorAll('[data-logout]').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            logoutUser();
        });
    });
    
    // Add click handlers to quick logout buttons
    document.querySelectorAll('[data-quick-logout]').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            quickLogout();
        });
    });
});

// Session timeout warning
let sessionTimeoutWarning = null;
let sessionTimeoutTimer = null;

function showSessionTimeoutWarning() {
    if (sessionTimeoutWarning) return; // Already showing
    
    sessionTimeoutWarning = document.createElement('div');
    sessionTimeoutWarning.className = 'alert alert-warning alert-dismissible position-fixed';
    sessionTimeoutWarning.style.cssText = 'top: 20px; left: 50%; transform: translateX(-50%); z-index: 9999; min-width: 400px;';
    sessionTimeoutWarning.innerHTML = `
        <i class="fas fa-clock me-2"></i>
        Your session will expire in 5 minutes. Click anywhere to stay logged in.
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    document.body.appendChild(sessionTimeoutWarning);
    
    // Auto-remove warning after 30 seconds
    setTimeout(() => {
        if (sessionTimeoutWarning && sessionTimeoutWarning.parentNode) {
            sessionTimeoutWarning.remove();
            sessionTimeoutWarning = null;
        }
    }, 30000);
}

// Reset session timeout
function resetSessionTimeout() {
    if (sessionTimeoutWarning) {
        sessionTimeoutWarning.remove();
        sessionTimeoutWarning = null;
    }
    
    // Clear existing timer
    if (sessionTimeoutTimer) {
        clearTimeout(sessionTimeoutTimer);
    }
    
    // Set new timer for 25 minutes (5 minutes before 30-minute session expires)
    sessionTimeoutTimer = setTimeout(showSessionTimeoutWarning, 25 * 60 * 1000);
}

// Start session timeout monitoring if user is logged in
if (document.querySelector('[data-logout]')) {
    resetSessionTimeout();
    
    // Reset timeout on any user activity
    ['click', 'keypress', 'scroll', 'mousemove'].forEach(event => {
        document.addEventListener(event, resetSessionTimeout, { passive: true, once: false });
    });
}
