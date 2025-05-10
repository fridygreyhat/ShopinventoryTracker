/**
 * Theme Switcher for Shop Inventory Management System
 * 
 * This script handles theme changes and persists them via user settings
 */

document.addEventListener('DOMContentLoaded', function() {
    // Theme previews in settings page
    const themePreviewElements = document.querySelectorAll('.theme-preview');
    const themeRadios = document.querySelectorAll('.theme-radio');
    
    // Apply Visual Preview Effects
    themePreviewElements.forEach(preview => {
        preview.addEventListener('click', function() {
            // Get the theme value from the data attribute
            const theme = this.getAttribute('data-theme');
            
            // Find the corresponding radio button and select it
            const radio = document.getElementById(`theme_${theme}`);
            if (radio) {
                radio.checked = true;
                
                // Trigger a preview of the theme without saving
                previewTheme(theme);
            }
        });
    });
    
    // Apply theme when radio buttons are clicked
    themeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.checked) {
                previewTheme(this.value);
            }
        });
    });
    
    // Save appearance settings
    const saveAppearanceBtn = document.getElementById('saveAppearanceSettings');
    if (saveAppearanceBtn) {
        saveAppearanceBtn.addEventListener('click', function() {
            saveThemeSettings();
        });
    }
    
    /**
     * Apply a theme temporarily for preview
     */
    function previewTheme(theme) {
        document.body.setAttribute('data-theme', theme);
        
        // Update selected state for previews
        themePreviewElements.forEach(preview => {
            if (preview.getAttribute('data-theme') === theme) {
                preview.classList.add('selected');
            } else {
                preview.classList.remove('selected');
            }
        });
        
        // Handle Bootstrap dark/light mode if needed
        if (theme === 'dark') {
            document.documentElement.setAttribute('data-bs-theme', 'dark');
        } else {
            document.documentElement.setAttribute('data-bs-theme', 'light');
        }
    }
    
    /**
     * Save theme settings to server
     */
    function saveThemeSettings() {
        // Get the selected theme
        const selectedTheme = document.querySelector('input[name="theme"]:checked').value;
        
        // Get other appearance settings
        const itemsPerPage = document.getElementById('items_per_page').value;
        const dateFormat = document.getElementById('date_format').value;
        
        // Show saving indicator
        const saveBtn = document.getElementById('saveAppearanceSettings');
        const originalText = saveBtn.textContent;
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
        
        // Save settings via API
        fetch('/api/settings/appearance', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                theme: selectedTheme,
                itemsPerPage: itemsPerPage,
                dateFormat: dateFormat
            }),
        })
        .then(response => response.json())
        .then(data => {
            // Reset button
            saveBtn.disabled = false;
            saveBtn.textContent = originalText;
            
            // Show success feedback
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-success mt-3';
            alertDiv.textContent = 'Settings saved successfully!';
            
            const form = document.getElementById('appearanceSettingsForm');
            form.appendChild(alertDiv);
            
            // Remove alert after 3 seconds
            setTimeout(() => {
                alertDiv.remove();
            }, 3000);
            
            // Apply the theme permanently
            document.body.setAttribute('data-theme', selectedTheme);
            
            // Update HTML theme if needed
            if (selectedTheme === 'dark') {
                document.documentElement.setAttribute('data-bs-theme', 'dark');
            } else {
                document.documentElement.setAttribute('data-bs-theme', 'light');
            }
        })
        .catch(error => {
            console.error('Error saving theme settings:', error);
            
            // Reset button
            saveBtn.disabled = false;
            saveBtn.textContent = originalText;
            
            // Show error feedback
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-danger mt-3';
            alertDiv.textContent = 'Error saving settings. Please try again.';
            
            const form = document.getElementById('appearanceSettingsForm');
            form.appendChild(alertDiv);
            
            // Remove alert after 3 seconds
            setTimeout(() => {
                alertDiv.remove();
            }, 3000);
        });
    }
    
    // Set up initial preview state - add "selected" class to the active theme
    const currentTheme = document.body.getAttribute('data-theme');
    themePreviewElements.forEach(preview => {
        if (preview.getAttribute('data-theme') === currentTheme) {
            preview.classList.add('selected');
        }
    });
});