
/**
 * Enhanced Tab Scrolling Manager
 * Handles horizontal tab scrolling with smooth behavior and visual indicators
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeTabScrolling();
});

function initializeTabScrolling() {
    const tabContainers = document.querySelectorAll('.nav-tabs');
    
    tabContainers.forEach(container => {
        enhanceTabScrolling(container);
    });
}

function enhanceTabScrolling(tabContainer) {
    // Wrap tab container if not already wrapped
    if (!tabContainer.parentElement.classList.contains('nav-tabs-wrapper')) {
        const wrapper = document.createElement('div');
        wrapper.className = 'nav-tabs-wrapper';
        tabContainer.parentNode.insertBefore(wrapper, tabContainer);
        wrapper.appendChild(tabContainer);
    }
    
    const wrapper = tabContainer.parentElement;
    
    // Update scroll indicators
    function updateScrollIndicators() {
        const { scrollLeft, scrollWidth, clientWidth } = tabContainer;
        const canScrollLeft = scrollLeft > 5;
        const canScrollRight = scrollLeft < scrollWidth - clientWidth - 5;
        
        wrapper.classList.toggle('can-scroll-left', canScrollLeft);
        wrapper.classList.toggle('can-scroll-right', canScrollRight);
    }
    
    // Smooth scroll to active tab
    function scrollToActiveTab() {
        const activeTab = tabContainer.querySelector('.nav-link.active');
        if (activeTab) {
            const tabRect = activeTab.getBoundingClientRect();
            const containerRect = tabContainer.getBoundingClientRect();
            
            if (tabRect.left < containerRect.left || tabRect.right > containerRect.right) {
                activeTab.scrollIntoView({
                    behavior: 'smooth',
                    block: 'nearest',
                    inline: 'center'
                });
            }
        }
    }
    
    // Handle keyboard navigation
    function handleKeyboardNavigation(e) {
        if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
            e.preventDefault();
            const direction = e.key === 'ArrowLeft' ? -1 : 1;
            const scrollAmount = 100;
            
            tabContainer.scrollBy({
                left: direction * scrollAmount,
                behavior: 'smooth'
            });
        }
    }
    
    // Handle touch/mouse wheel scrolling
    function handleWheelScroll(e) {
        if (e.deltaY !== 0) {
            e.preventDefault();
            tabContainer.scrollBy({
                left: e.deltaY,
                behavior: 'smooth'
            });
        }
    }
    
    // Add event listeners
    tabContainer.addEventListener('scroll', updateScrollIndicators);
    tabContainer.addEventListener('keydown', handleKeyboardNavigation);
    tabContainer.addEventListener('wheel', handleWheelScroll, { passive: false });
    
    // Handle window resize
    window.addEventListener('resize', () => {
        setTimeout(updateScrollIndicators, 100);
    });
    
    // Handle tab clicks to ensure active tab is visible
    const tabLinks = tabContainer.querySelectorAll('.nav-link');
    tabLinks.forEach(link => {
        link.addEventListener('click', () => {
            setTimeout(scrollToActiveTab, 100);
        });
    });
    
    // Initial setup
    setTimeout(() => {
        updateScrollIndicators();
        scrollToActiveTab();
    }, 100);
    
    // Mutation observer to handle dynamic tab changes
    const observer = new MutationObserver(() => {
        setTimeout(() => {
            updateScrollIndicators();
            scrollToActiveTab();
        }, 50);
    });
    
    observer.observe(tabContainer, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['class']
    });
}

// Auto-initialize on dynamic content
function initializeNewTabs() {
    const newTabContainers = document.querySelectorAll('.nav-tabs:not([data-scroll-enhanced])');
    newTabContainers.forEach(container => {
        container.setAttribute('data-scroll-enhanced', 'true');
        enhanceTabScrolling(container);
    });
}

// Export for manual initialization
window.TabScrollEnhancer = {
    initialize: initializeTabScrolling,
    enhance: enhanceTabScrolling,
    initializeNew: initializeNewTabs
};
