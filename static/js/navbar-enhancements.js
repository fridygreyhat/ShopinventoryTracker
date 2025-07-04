
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

    // Enhanced scroll management with improved feedback
    if (sidebarBody) {
        let scrollTimeout;
        let isScrolling = false;
        
        function updateScrollIndicators() {
            if (!sidebarBody) return;
            
            const scrollTop = sidebarBody.scrollTop;
            const scrollHeight = sidebarBody.scrollHeight;
            const clientHeight = sidebarBody.clientHeight;
            const isScrollable = scrollHeight > clientHeight;
            
            console.log('Scroll Debug:', {
                scrollTop,
                scrollHeight,
                clientHeight,
                isScrollable
            });
            
            // Only show indicators if content is scrollable
            if (!isScrollable) {
                sidebarBody.classList.remove('can-scroll-up', 'can-scroll-down');
                return;
            }
            
            // Show top indicator if scrolled down
            if (scrollTop > 20) {
                sidebarBody.classList.add('can-scroll-up');
            } else {
                sidebarBody.classList.remove('can-scroll-up');
            }
            
            // Show bottom indicator if can scroll down
            if (scrollTop < scrollHeight - clientHeight - 20) {
                sidebarBody.classList.add('can-scroll-down');
            } else {
                sidebarBody.classList.remove('can-scroll-down');
            }
            
            // Add scrolling class for visual feedback
            if (isScrolling) {
                sidebarBody.classList.add('is-scrolling');
            }
        }
        
        function handleScrollStart() {
            isScrolling = true;
            sidebarBody.classList.add('is-scrolling');
        }
        
        function handleScrollEnd() {
            isScrolling = false;
            sidebarBody.classList.remove('is-scrolling');
        }
        
        sidebarBody.addEventListener('scroll', function() {
            handleScrollStart();
            clearTimeout(scrollTimeout);
            
            scrollTimeout = setTimeout(() => {
                saveScrollPosition();
                handleScrollEnd();
            }, 150);
            
            updateScrollIndicators();
        });

        // Handle touch scrolling for mobile
        let touchStartY = 0;
        let touchEndY = 0;
        
        sidebarBody.addEventListener('touchstart', function(e) {
            touchStartY = e.changedTouches[0].screenY;
            handleScrollStart();
        });
        
        sidebarBody.addEventListener('touchend', function(e) {
            touchEndY = e.changedTouches[0].screenY;
            setTimeout(handleScrollEnd, 100);
        });

        // Initial setup
        setTimeout(() => {
            // Force recalculate sidebar body height
            if (sidebarBody) {
                const sidebarHeader = document.querySelector('.sidebar-header');
                const sidebarFooter = document.querySelector('.sidebar-footer');
                const userProfile = document.querySelector('.user-profile');
                
                let reservedHeight = 0;
                if (sidebarHeader) reservedHeight += sidebarHeader.offsetHeight;
                if (sidebarFooter) reservedHeight += sidebarFooter.offsetHeight;
                if (userProfile) reservedHeight += userProfile.offsetHeight;
                
                sidebarBody.style.maxHeight = `calc(100vh - ${reservedHeight + 40}px)`;
                sidebarBody.style.height = `calc(100vh - ${reservedHeight + 40}px)`;
            }
            
            updateScrollIndicators();
            
            // Smooth scroll to active nav item
            const activeNavLink = document.querySelector('.nav-link.active');
            if (activeNavLink) {
                activeNavLink.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
                // Update indicators after scrolling to active item
                setTimeout(updateScrollIndicators, 500);
            }
        }, 200);
        
        // Update scroll indicators on resize and orientation change
        window.addEventListener('resize', () => {
            setTimeout(updateScrollIndicators, 100);
        });
        
        window.addEventListener('orientationchange', () => {
            setTimeout(updateScrollIndicators, 300);
        });
        
        // Keyboard navigation support
        sidebarBody.addEventListener('keydown', function(e) {
            if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
                e.preventDefault();
                const currentActive = document.querySelector('.nav-link.active');
                const allNavLinks = Array.from(document.querySelectorAll('.nav-link'));
                
                if (currentActive) {
                    const currentIndex = allNavLinks.indexOf(currentActive);
                    let nextIndex;
                    
                    if (e.key === 'ArrowUp') {
                        nextIndex = currentIndex > 0 ? currentIndex - 1 : allNavLinks.length - 1;
                    } else {
                        nextIndex = currentIndex < allNavLinks.length - 1 ? currentIndex + 1 : 0;
                    }
                    
                    const nextLink = allNavLinks[nextIndex];
                    if (nextLink) {
                        nextLink.focus();
                        nextLink.scrollIntoView({
                            behavior: 'smooth',
                            block: 'nearest'
                        });
                    }
                }
            }
        });
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
