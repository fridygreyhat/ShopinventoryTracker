
// Mobile optimizations for inventory management system
document.addEventListener('DOMContentLoaded', function() {
    // Check if device is mobile
    const isMobile = window.innerWidth <= 768;
    const isTouch = 'ontouchstart' in window;
    
    if (isMobile || isTouch) {
        initMobileOptimizations();
    }
    
    // Handle orientation changes
    window.addEventListener('orientationchange', function() {
        setTimeout(function() {
            adjustForOrientation();
        }, 100);
    });
    
    // Handle resize events
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            adjustForScreenSize();
        }, 250);
    });
});

function initMobileOptimizations() {
    // Add mobile-specific classes
    document.body.classList.add('mobile-optimized');
    
    // Optimize tables for mobile
    optimizeTablesForMobile();
    
    // Add touch-friendly interactions
    addTouchFriendlyInteractions();
    
    // Optimize modals for mobile
    optimizeModalsForMobile();
    
    // Add pull-to-refresh functionality
    addPullToRefresh();
    
    // Optimize form inputs for mobile
    optimizeFormsForMobile();
}

function optimizeTablesForMobile() {
    const tables = document.querySelectorAll('.table-responsive');
    
    tables.forEach(table => {
        // Add horizontal scroll indicator
        const scrollIndicator = document.createElement('div');
        scrollIndicator.className = 'scroll-indicator d-block d-md-none';
        scrollIndicator.innerHTML = '<small class="text-muted"><i class="fas fa-arrows-alt-h me-1"></i>Scroll horizontally to see more</small>';
        table.parentNode.insertBefore(scrollIndicator, table);
        
        // Add scroll event listener to hide/show indicator
        table.addEventListener('scroll', function() {
            if (table.scrollLeft > 0) {
                scrollIndicator.style.opacity = '0.5';
            } else {
                scrollIndicator.style.opacity = '1';
            }
        });
        
        // Add mobile-friendly row tap functionality
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            row.style.cursor = 'pointer';
            row.addEventListener('touchstart', function() {
                this.style.backgroundColor = 'rgba(0,0,0,0.05)';
            });
            row.addEventListener('touchend', function() {
                setTimeout(() => {
                    this.style.backgroundColor = '';
                }, 150);
            });
        });
    });
}

function addTouchFriendlyInteractions() {
    // Add ripple effect to buttons
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('touchstart', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.touches[0].clientX - rect.left - size / 2;
            const y = e.touches[0].clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple');
            
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
    
    // Add swipe gestures for cards
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        let startX, startY, startTime;
        
        card.addEventListener('touchstart', function(e) {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            startTime = new Date().getTime();
        });
        
        card.addEventListener('touchend', function(e) {
            if (!startX || !startY) return;
            
            const endX = e.changedTouches[0].clientX;
            const endY = e.changedTouches[0].clientY;
            const endTime = new Date().getTime();
            
            const diffX = startX - endX;
            const diffY = startY - endY;
            const diffTime = endTime - startTime;
            
            // Check for swipe (minimum distance and maximum time)
            if (Math.abs(diffX) > 50 && Math.abs(diffY) < 100 && diffTime < 300) {
                if (diffX > 0) {
                    // Swiped left - could trigger actions like delete or archive
                    card.classList.add('swiped-left');
                } else {
                    // Swiped right - could trigger actions like edit or favorite
                    card.classList.add('swiped-right');
                }
                
                setTimeout(() => {
                    card.classList.remove('swiped-left', 'swiped-right');
                }, 300);
            }
            
            startX = startY = null;
        });
    });
}

function optimizeModalsForMobile() {
    const modals = document.querySelectorAll('.modal');
    
    modals.forEach(modal => {
        // Make modals full-screen on mobile
        if (window.innerWidth <= 576) {
            const modalDialog = modal.querySelector('.modal-dialog');
            modalDialog.classList.add('modal-fullscreen-sm-down');
        }
        
        // Add touch-friendly close button
        const closeButton = modal.querySelector('.btn-close');
        if (closeButton) {
            closeButton.style.minWidth = '44px';
            closeButton.style.minHeight = '44px';
        }
    });
}

function addPullToRefresh() {
    let startY = 0;
    let isPulling = false;
    const threshold = 100;
    
    document.addEventListener('touchstart', function(e) {
        if (window.scrollY === 0) {
            startY = e.touches[0].clientY;
        }
    });
    
    document.addEventListener('touchmove', function(e) {
        if (window.scrollY === 0 && startY < e.touches[0].clientY) {
            const pullDistance = e.touches[0].clientY - startY;
            
            if (pullDistance > threshold && !isPulling) {
                isPulling = true;
                showPullToRefreshIndicator();
            }
        }
    });
    
    document.addEventListener('touchend', function() {
        if (isPulling) {
            isPulling = false;
            hidePullToRefreshIndicator();
            // Refresh the current page data
            if (typeof refreshPageData === 'function') {
                refreshPageData();
            } else {
                location.reload();
            }
        }
        startY = 0;
    });
}

function showPullToRefreshIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'pull-refresh-indicator';
    indicator.className = 'fixed-top bg-primary text-white text-center py-2';
    indicator.innerHTML = '<i class="fas fa-sync-alt fa-spin me-2"></i>Release to refresh';
    document.body.appendChild(indicator);
}

function hidePullToRefreshIndicator() {
    const indicator = document.getElementById('pull-refresh-indicator');
    if (indicator) {
        indicator.remove();
    }
}

function optimizeFormsForMobile() {
    // Improve form input experience on mobile
    const inputs = document.querySelectorAll('input, textarea, select');
    
    inputs.forEach(input => {
        // Add proper input types for mobile keyboards
        if (input.type === 'text') {
            if (input.name && input.name.includes('email')) {
                input.type = 'email';
            } else if (input.name && (input.name.includes('phone') || input.name.includes('tel'))) {
                input.type = 'tel';
            } else if (input.name && (input.name.includes('number') || input.name.includes('quantity') || input.name.includes('price'))) {
                input.type = 'number';
            }
        }
        
        // Prevent zoom on focus for iOS
        if (parseFloat(input.style.fontSize) < 16) {
            input.style.fontSize = '16px';
        }
        
        // Add touch-friendly focus styles
        input.addEventListener('focus', function() {
            this.scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
    });
}

function adjustForOrientation() {
    // Adjust layout based on orientation
    const isLandscape = window.innerWidth > window.innerHeight;
    
    if (isLandscape) {
        document.body.classList.add('landscape');
        document.body.classList.remove('portrait');
    } else {
        document.body.classList.add('portrait');
        document.body.classList.remove('landscape');
    }
    
    // Adjust chart sizes
    const charts = document.querySelectorAll('canvas');
    charts.forEach(chart => {
        if (chart.chart) {
            chart.chart.resize();
        }
    });
}

function adjustForScreenSize() {
    const isMobile = window.innerWidth <= 768;
    
    // Adjust table column visibility
    const mobileCols = document.querySelectorAll('.d-none-mobile');
    const tabletCols = document.querySelectorAll('.d-none-tablet');
    
    if (window.innerWidth <= 576) {
        mobileCols.forEach(col => col.style.display = 'none');
    } else {
        mobileCols.forEach(col => col.style.display = '');
    }
    
    if (window.innerWidth <= 768) {
        tabletCols.forEach(col => col.style.display = 'none');
    } else {
        tabletCols.forEach(col => col.style.display = '');
    }
}

// Add CSS for mobile enhancements
const mobileCSS = `
.mobile-optimized .ripple {
    position: absolute;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.3);
    transform: scale(0);
    animation: ripple-animation 0.6s linear;
    pointer-events: none;
}

@keyframes ripple-animation {
    to {
        transform: scale(4);
        opacity: 0;
    }
}

.swiped-left {
    transform: translateX(-10px);
    transition: transform 0.3s ease;
}

.swiped-right {
    transform: translateX(10px);
    transition: transform 0.3s ease;
}

.scroll-indicator {
    padding: 0.5rem;
    background: rgba(0, 0, 0, 0.05);
    border-radius: 4px;
    margin-bottom: 0.5rem;
    transition: opacity 0.3s ease;
}

@media (max-width: 576px) {
    .modal-fullscreen-sm-down {
        width: 100vw;
        max-width: none;
        height: 100vh;
        margin: 0;
    }
    
    .modal-fullscreen-sm-down .modal-content {
        height: 100vh;
        border: 0;
        border-radius: 0;
    }
}
`;

// Inject mobile CSS
const style = document.createElement('style');
style.textContent = mobileCSS;
document.head.appendChild(style);
