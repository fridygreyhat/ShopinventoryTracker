
// Vertical Sidebar Navigation JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const notificationBtn = document.getElementById('notificationBtn');
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    const sidebarBody = document.querySelector('.sidebar-body');

    // Mobile menu toggle
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', function() {
            sidebar.classList.add('show');
            sidebarOverlay.classList.add('show');
            document.body.style.overflow = 'hidden';
        });
    }

    // Sidebar close button
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            closeSidebar();
        });
    }

    // Overlay click to close sidebar
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function() {
            closeSidebar();
        });
    }

    // Close sidebar function
    function closeSidebar() {
        sidebar.classList.remove('show');
        sidebarOverlay.classList.remove('show');
        document.body.style.overflow = '';
    }

    // Fullscreen toggle
    if (fullscreenBtn) {
        fullscreenBtn.addEventListener('click', function() {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen().then(() => {
                    this.innerHTML = '<i class="fas fa-compress"></i>';
                });
            } else {
                document.exitFullscreen().then(() => {
                    this.innerHTML = '<i class="fas fa-expand"></i>';
                });
            }
        });
    }

    // Notification button (placeholder functionality)
    if (notificationBtn) {
        notificationBtn.addEventListener('click', function() {
            // Toggle notification panel or show toast
            showNotificationToast();
        });
    }

    function showNotificationToast() {
        // Create and show a bootstrap toast for notifications
        const toastHtml = `
            <div class="toast align-items-center text-white bg-info border-0 position-fixed top-0 end-0 m-3" role="alert" style="z-index: 9999;">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fas fa-info-circle me-2"></i>
                        You have 3 new notifications
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', toastHtml);
        const toast = new bootstrap.Toast(document.querySelector('.toast:last-child'));
        toast.show();
    }

    // Active nav link highlighting
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth > 991.98) {
            closeSidebar();
        }
    });

    // Smooth scroll for nav links
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Add loading animation
            const icon = this.querySelector('.nav-icon');
            const originalIcon = icon.innerHTML;
            icon.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            
            setTimeout(() => {
                icon.innerHTML = originalIcon;
            }, 500);
        });
    });

    // Auto-collapse sidebar on mobile when clicking nav links
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 991.98) {
                setTimeout(() => {
                    closeSidebar();
                }, 300);
            }
        });
    });

    // Sidebar scroll position management
    function saveScrollPosition() {
        if (sidebarBody) {
            localStorage.setItem('sidebarScrollPosition', sidebarBody.scrollTop);
        }
    }

    function restoreScrollPosition() {
        if (sidebarBody) {
            const savedPosition = localStorage.getItem('sidebarScrollPosition');
            if (savedPosition) {
                sidebarBody.scrollTop = parseInt(savedPosition);
            }
        }
    }

    // Save scroll position when navigating away
    window.addEventListener('beforeunload', saveScrollPosition);

    // Restore scroll position on load
    restoreScrollPosition();

    // Add scroll position saving on scroll
    if (sidebarBody) {
        let scrollTimeout;
        
        function updateScrollIndicators() {
            const scrollTop = sidebarBody.scrollTop;
            const scrollHeight = sidebarBody.scrollHeight;
            const clientHeight = sidebarBody.clientHeight;
            
            // Show top indicator if scrolled down
            if (scrollTop > 10) {
                sidebarBody.classList.add('can-scroll-up');
            } else {
                sidebarBody.classList.remove('can-scroll-up');
            }
            
            // Show bottom indicator if can scroll down
            if (scrollTop < scrollHeight - clientHeight - 10) {
                sidebarBody.classList.add('can-scroll-down');
            } else {
                sidebarBody.classList.remove('can-scroll-down');
            }
        }
        
        sidebarBody.addEventListener('scroll', function() {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(saveScrollPosition, 150);
            updateScrollIndicators();
        });

        // Initial scroll indicator check
        updateScrollIndicators();

        // Smooth scroll to active nav item
        const activeNavLink = document.querySelector('.nav-link.active');
        if (activeNavLink) {
            setTimeout(() => {
                activeNavLink.scrollIntoView({
                    behavior: 'smooth',
                    block: 'nearest'
                });
                // Update indicators after scrolling to active item
                setTimeout(updateScrollIndicators, 300);
            }, 100);
        }
        
        // Update scroll indicators on resize
        window.addEventListener('resize', updateScrollIndicators);
    }

    console.log('Vertical sidebar navigation initialized');
});

// Escape key to close sidebar
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const sidebar = document.getElementById('sidebar');
        const sidebarOverlay = document.getElementById('sidebarOverlay');
        
        if (sidebar && sidebar.classList.contains('show')) {
            sidebar.classList.remove('show');
            sidebarOverlay.classList.remove('show');
            document.body.style.overflow = '';
        }
    }
});
