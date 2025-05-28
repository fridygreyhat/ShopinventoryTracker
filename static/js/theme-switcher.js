/**
 * Theme Switcher Module
 * Handles theme switching functionality for the Shop Inventory Management System
 */

// Available themes
const AVAILABLE_THEMES = [
    'tanzanite', // Default theme
    'forest',
    'ocean',
    'sunset',
    'dark'
];

// DOM variables
let themeSelectors;
let currentTheme = 'sunset'; // Default theme

/**
 * Initialize theme from stored preference or default
 */
function initTheme() {
    console.log('Theme switcher initializing...');

    // Check what's already on the body
    const bodyTheme = document.body.getAttribute('data-theme-value');
    console.log('Current body theme attribute:', bodyTheme);

    // Check if theme is stored in local storage
    const storedTheme = localStorage.getItem('user_theme');
    console.log('Theme from localStorage:', storedTheme);

    // Set theme from storage, session, or default to tanzanite
    if (storedTheme && AVAILABLE_THEMES.includes(storedTheme)) {
        console.log('Using theme from localStorage:', storedTheme);
        setTheme(storedTheme);
    } else {
        console.log('No valid theme in localStorage, fetching from server...');
        // Try to get theme from session if it exists
        fetch('/api/settings/get/user_theme')
            .then(response => response.json())
            .then(data => {
                console.log('Theme API response:', data);
                if (data.success && data.value && AVAILABLE_THEMES.includes(data.value)) {
                    console.log('Using theme from server:', data.value);
                    setTheme(data.value);
                } else {
                    console.log('No valid theme from server, using default: sunset');
                    setTheme('sunset'); // Default theme
                }
            })
            .catch(error => {
                console.error('Error fetching theme setting:', error);
                console.log('Error fetching theme, using default: sunset');
                setTheme('sunset'); // Default theme on error
            });
    }

    // Initialize theme selectors if on settings page
    themeSelectors = document.querySelectorAll('.theme-preview');
    console.log('Theme selectors found:', themeSelectors ? themeSelectors.length : 0);
    if (themeSelectors && themeSelectors.length > 0) {
        // Initialize theme selection UI
        initThemeSelectors();
    }
}

/**
 * Set the active theme
 * @param {string} theme - Theme name to activate
 */
function setTheme(theme) {
    console.log('Setting theme to:', theme);

    if (!AVAILABLE_THEMES.includes(theme)) {
        console.error(`Theme "${theme}" is not available`);
        return;
    }

    // Update body data attribute
    document.body.setAttribute('data-theme-value', theme);
    console.log('Updated body data-theme-value to:', theme);

    // Store in local storage
    localStorage.setItem('user_theme', theme);
    console.log('Saved theme to localStorage');

    // Update current theme variable
    currentTheme = theme;

    // Update theme selectors if on settings page
    updateThemeSelectors(theme);

    // Apply CSS variables (if needed)
    console.log('Theme applied to document body');
}

/**
 * Save theme preference to server
 * @param {string} theme - Theme name to save
 */
function saveThemePreference(theme) {
    fetch('/api/settings/appearance', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            theme: theme,
            itemsPerPage: '25', // Default
            dateFormat: 'YYYY-MM-DD' // Default
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            console.error('Error saving theme preference:', data.error || 'Unknown error');
        }
    })
    .catch(error => {
        console.error('Network error when saving theme preference:', error);
    });
}

/**
 * Initialize theme selectors on settings page
 */
function initThemeSelectors() {
    themeSelectors.forEach(selector => {
        // Get theme value from data attribute
        const theme = selector.getAttribute('data-theme-value');

        // Add click event listener
        selector.addEventListener('click', () => {
            setTheme(theme);
            saveThemePreference(theme);
        });

        // Mark as selected if current theme
        if (theme === currentTheme) {
            selector.classList.add('selected');
        }
    });
}

/**
 * Update theme selectors to show current selection
 * @param {string} activeTheme - Currently active theme
 */
function updateThemeSelectors(activeTheme) {
    if (!themeSelectors || themeSelectors.length === 0) return;

    themeSelectors.forEach(selector => {
        const theme = selector.getAttribute('data-theme-value');

        if (theme === activeTheme) {
            selector.classList.add('selected');
        } else {
            selector.classList.remove('selected');
        }
    });
}

// Initialize theme when DOM is loaded
document.addEventListener('DOMContentLoaded', initTheme);

// Make functions available globally instead of using exports
window.setTheme = setTheme;
window.saveThemePreference = saveThemePreference;