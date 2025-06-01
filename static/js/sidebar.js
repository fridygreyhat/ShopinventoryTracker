
// Sidebar Management JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const mobileSidebarToggle = document.getElementById('mobileSidebarToggle');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const mainContent = document.getElementById('mainContent');
    
    // Check if elements exist
    if (!sidebar || !sidebarToggle) {
        console.warn('Sidebar elements not found');
        return;
    }
    
    // Get sidebar state from localStorage
    const getSidebarState = () => {
        return localStorage.getItem('sidebarCollapsed') === 'true';
    };
    
    // Save sidebar state to localStorage
    const setSidebarState = (collapsed) => {
        localStorage.setItem('sidebarCollapsed', collapsed.toString());
    };
    
    // Apply sidebar state
    const applySidebarState = (collapsed) => {
        if (collapsed) {
            sidebar.classList.add('collapsed');
        } else {
            sidebar.classList.remove('collapsed');
        }
        setSidebarState(collapsed);
    };
    
    // Initialize sidebar state
    const initSidebarState = () => {
        const isCollapsed = getSidebarState();
        applySidebarState(isCollapsed);
        
        // On mobile, always start collapsed
        if (window.innerWidth < 992) {
            sidebar.classList.remove('show');
            if (sidebarOverlay) {
                sidebarOverlay.classList.remove('show');
            }
        }
    };
    
    // Toggle sidebar (desktop)
    const toggleSidebar = () => {
        const isCollapsed = sidebar.classList.contains('collapsed');
        applySidebarState(!isCollapsed);
    };
    
    // Show mobile sidebar
    const showMobileSidebar = () => {
        sidebar.classList.add('show');
        if (sidebarOverlay) {
            sidebarOverlay.classList.add('show');
        }
        document.body.style.overflow = 'hidden';
    };
    
    // Hide mobile sidebar
    const hideMobileSidebar = () => {
        sidebar.classList.remove('show');
        if (sidebarOverlay) {
            sidebarOverlay.classList.remove('show');
        }
        document.body.style.overflow = '';
    };
    
    // Event listeners
    sidebarToggle.addEventListener('click', function(e) {
        e.preventDefault();
        if (window.innerWidth >= 992) {
            toggleSidebar();
        } else {
            hideMobileSidebar();
        }
    });
    
    if (mobileSidebarToggle) {
        mobileSidebarToggle.addEventListener('click', function(e) {
            e.preventDefault();
            showMobileSidebar();
        });
    }
    
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function() {
            hideMobileSidebar();
        });
    }
    
    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth >= 992) {
            // Desktop mode
            hideMobileSidebar();
            const isCollapsed = getSidebarState();
            applySidebarState(isCollapsed);
        } else {
            // Mobile mode
            sidebar.classList.remove('collapsed');
            hideMobileSidebar();
        }
    });
    
    // Handle escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && window.innerWidth < 992) {
            hideMobileSidebar();
        }
    });
    
    // Handle sidebar link clicks on mobile
    const sidebarLinks = sidebar.querySelectorAll('.sidebar-link');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth < 992) {
                // Small delay to allow navigation to start
                setTimeout(() => {
                    hideMobileSidebar();
                }, 100);
            }
        });
    });
    
    // Add active states and ripple effects
    sidebarLinks.forEach(link => {
        // Add ripple effect on click
        link.addEventListener('click', function(e) {
            if (this.classList.contains('dropdown-toggle')) {
                return; // Skip ripple for dropdown toggles
            }
            
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                left: ${x}px;
                top: ${y}px;
                background: rgba(76, 80, 197, 0.3);
                border-radius: 50%;
                transform: scale(0);
                animation: sidebar-ripple 0.6s linear;
                pointer-events: none;
                z-index: 1;
            `;
            
            this.style.position = 'relative';
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
    
    // Initialize on page load
    initSidebarState();
    
    // Update active link based on current path
    const updateActiveLink = () => {
        const currentPath = window.location.pathname;
        sidebarLinks.forEach(link => {
            const linkPath = new URL(link.href, window.location.origin).pathname;
            if (linkPath === currentPath) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    };
    
    updateActiveLink();
    
    // Handle navigation changes (for SPAs)
    window.addEventListener('popstate', updateActiveLink);
    
    // Smooth scrolling for sidebar navigation
    const smoothScrollToTop = () => {
        if (mainContent) {
            mainContent.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        }
    };
    
    // Add smooth scroll on navigation
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function() {
            // Only scroll if it's not a dropdown toggle
            if (!this.classList.contains('dropdown-toggle')) {
                smoothScrollToTop();
            }
        });
    });
});

// Add ripple animation CSS
const sidebarRippleCSS = `
@keyframes sidebar-ripple {
    to {
        transform: scale(4);
        opacity: 0;
    }
}
`;

// Only add CSS if it doesn't exist
if (!document.querySelector('#sidebar-ripple-styles')) {
    const style = document.createElement('style');
    style.id = 'sidebar-ripple-styles';
    style.textContent = sidebarRippleCSS;
    document.head.appendChild(style);
}

// Sidebar tooltip functionality for collapsed state
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    
    if (!sidebar) return;
    
    // Create tooltip element
    const tooltip = document.createElement('div');
    tooltip.className = 'sidebar-tooltip';
    tooltip.style.cssText = `
        position: fixed;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 0.5rem 0.75rem;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 500;
        z-index: 1060;
        pointer-events: none;
        opacity: 0;
        transition: all 0.2s ease;
        white-space: nowrap;
    `;
    document.body.appendChild(tooltip);
    
    // Show tooltip on hover when collapsed
    const sidebarLinks = sidebar.querySelectorAll('.sidebar-link');
    sidebarLinks.forEach(link => {
        const textElement = link.querySelector('.sidebar-text');
        if (!textElement) return;
        
        link.addEventListener('mouseenter', function(e) {
            if (sidebar.classList.contains('collapsed')) {
                const text = textElement.textContent.trim();
                if (text) {
                    tooltip.textContent = text;
                    tooltip.style.opacity = '1';
                    
                    const rect = this.getBoundingClientRect();
                    tooltip.style.left = (rect.right + 10) + 'px';
                    tooltip.style.top = (rect.top + rect.height / 2 - tooltip.offsetHeight / 2) + 'px';
                }
            }
        });
        
        link.addEventListener('mouseleave', function() {
            tooltip.style.opacity = '0';
        });
    });
    
    // Hide tooltip when sidebar is expanded
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.attributeName === 'class') {
                if (!sidebar.classList.contains('collapsed')) {
                    tooltip.style.opacity = '0';
                }
            }
        });
    });
    
    observer.observe(sidebar, { attributes: true });
});
