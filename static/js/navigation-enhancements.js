/**
 * Navigation and Tab Scrolling Enhancements
 * Fixes vertical navigation bar positioning and tab scrolling issues
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize tab scrolling enhancements
    initializeTabScrolling();
    
    // Initialize sidebar position fixes
    initializeSidebarFixes();
    
    // Remove excessive scroll debug logging
    removeScrollDebugNoise();
});

/**
 * Enhance tab navigation with smooth scrolling and responsive behavior
 */
function initializeTabScrolling() {
    const tabContainers = document.querySelectorAll('.nav-tabs');
    
    tabContainers.forEach(container => {
        // Add scroll indicators for tab overflow
        addTabScrollIndicators(container);
        
        // Enable smooth scrolling for tab navigation
        enableSmoothTabScrolling(container);
        
        // Auto-scroll to active tab
        scrollToActiveTab(container);
    });
}

/**
 * Add visual indicators when tabs are scrollable
 */
function addTabScrollIndicators(tabContainer) {
    const wrapper = document.createElement('div');
    wrapper.className = 'tab-scroll-wrapper position-relative';
    
    tabContainer.parentNode.insertBefore(wrapper, tabContainer);
    wrapper.appendChild(tabContainer);
    
    // Left scroll indicator
    const leftIndicator = document.createElement('div');
    leftIndicator.className = 'tab-scroll-indicator tab-scroll-left';
    leftIndicator.innerHTML = '<i class="fas fa-chevron-left"></i>';
    wrapper.appendChild(leftIndicator);
    
    // Right scroll indicator
    const rightIndicator = document.createElement('div');
    rightIndicator.className = 'tab-scroll-indicator tab-scroll-right';
    rightIndicator.innerHTML = '<i class="fas fa-chevron-right"></i>';
    wrapper.appendChild(rightIndicator);
    
    // Add indicator styles
    const style = document.createElement('style');
    style.textContent = `
        .tab-scroll-wrapper {
            position: relative;
        }
        
        .tab-scroll-indicator {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid var(--card-border);
            border-radius: 50%;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 10;
            transition: opacity 0.2s;
            opacity: 0;
            pointer-events: none;
        }
        
        .tab-scroll-indicator.visible {
            opacity: 1;
            pointer-events: all;
        }
        
        .tab-scroll-left {
            left: 5px;
        }
        
        .tab-scroll-right {
            right: 5px;
        }
        
        .tab-scroll-indicator:hover {
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
    `;
    
    if (!document.getElementById('tab-scroll-styles')) {
        style.id = 'tab-scroll-styles';
        document.head.appendChild(style);
    }
    
    // Update indicator visibility
    function updateIndicators() {
        const { scrollLeft, scrollWidth, clientWidth } = tabContainer;
        
        leftIndicator.classList.toggle('visible', scrollLeft > 0);
        rightIndicator.classList.toggle('visible', scrollLeft < scrollWidth - clientWidth);
    }
    
    // Scroll handlers
    leftIndicator.addEventListener('click', () => {
        tabContainer.scrollBy({ left: -100, behavior: 'smooth' });
    });
    
    rightIndicator.addEventListener('click', () => {
        tabContainer.scrollBy({ left: 100, behavior: 'smooth' });
    });
    
    tabContainer.addEventListener('scroll', updateIndicators);
    window.addEventListener('resize', updateIndicators);
    
    // Initial check
    setTimeout(updateIndicators, 100);
}

/**
 * Enable smooth scrolling behavior for tabs
 */
function enableSmoothTabScrolling(tabContainer) {
    tabContainer.style.scrollBehavior = 'smooth';
    
    // Handle keyboard navigation
    tabContainer.addEventListener('keydown', function(e) {
        if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
            e.preventDefault();
            const direction = e.key === 'ArrowLeft' ? -1 : 1;
            tabContainer.scrollBy({ left: direction * 100, behavior: 'smooth' });
        }
    });
}

/**
 * Automatically scroll to show the active tab
 */
function scrollToActiveTab(tabContainer) {
    const activeTab = tabContainer.querySelector('.nav-link.active');
    if (activeTab) {
        setTimeout(() => {
            activeTab.scrollIntoView({
                behavior: 'smooth',
                block: 'nearest',
                inline: 'center'
            });
        }, 100);
    }
}

/**
 * Fix sidebar positioning issues
 */
function initializeSidebarFixes() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.querySelector('.main-content');
    
    if (!sidebar || !mainContent) return;
    
    // Ensure sidebar doesn't interfere with main content scrolling
    function adjustLayout() {
        const sidebarWidth = sidebar.offsetWidth;
        const isMobile = window.innerWidth < 992;
        
        if (!isMobile) {
            mainContent.style.marginLeft = sidebarWidth + 'px';
            mainContent.style.maxWidth = `calc(100vw - ${sidebarWidth}px)`;
        } else {
            mainContent.style.marginLeft = '0';
            mainContent.style.maxWidth = '100vw';
        }
    }
    
    // Debounced resize handler
    let resizeTimeout;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(adjustLayout, 150);
    });
    
    // Initial adjustment
    adjustLayout();
    
    // Fix sidebar z-index conflicts
    sidebar.style.zIndex = '1050';
    
    // Prevent sidebar scroll from affecting main content
    sidebar.addEventListener('wheel', function(e) {
        e.stopPropagation();
    });
}

/**
 * Remove excessive scroll debug logging that clutters console
 */
function removeScrollDebugNoise() {
    // Override console.log temporarily to filter out scroll debug messages
    const originalLog = console.log;
    
    console.log = function(...args) {
        // Filter out scroll debug messages
        const message = args.join(' ');
        if (message.includes('Scroll Debug:') || 
            message.includes('scrollTop') || 
            message.includes('scrollHeight') ||
            message.includes('isScrollable')) {
            return; // Suppress these messages
        }
        
        // Allow other log messages
        originalLog.apply(console, args);
    };
    
    // Also handle potential scroll event listeners that might be causing issues
    const elements = document.querySelectorAll('[data-scroll-debug]');
    elements.forEach(el => {
        el.removeAttribute('data-scroll-debug');
    });
}

/**
 * Enhanced mobile menu handling
 */
function initializeMobileMenu() {
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    
    if (!mobileMenuBtn || !sidebar) return;
    
    mobileMenuBtn.addEventListener('click', () => {
        sidebar.classList.toggle('show');
        document.body.classList.toggle('sidebar-open');
    });
    
    if (overlay) {
        overlay.addEventListener('click', () => {
            sidebar.classList.remove('show');
            document.body.classList.remove('sidebar-open');
        });
    }
}

// Initialize mobile menu when DOM is ready
document.addEventListener('DOMContentLoaded', initializeMobileMenu);