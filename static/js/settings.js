document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const saveGeneralSettingsBtn = document.getElementById('saveGeneralSettings');
    const saveAppearanceSettingsBtn = document.getElementById('saveAppearanceSettings');
    const saveInventorySettingsBtn = document.getElementById('saveInventorySettings');
    const saveNotificationSettingsBtn = document.getElementById('saveNotificationSettings');
    const saveAdvancedSettingsBtn = document.getElementById('saveAdvancedSettings');
    
    // Initialize settings
    loadSettings();
    
    // Event Listeners
    saveGeneralSettingsBtn.addEventListener('click', function() {
        saveSettingsGroup('generalSettingsForm', 'general');
    });
    
    saveAppearanceSettingsBtn.addEventListener('click', function() {
        saveSettingsGroup('appearanceSettingsForm', 'appearance');
    });
    
    saveInventorySettingsBtn.addEventListener('click', function() {
        saveSettingsGroup('inventorySettingsForm', 'inventory');
    });
    
    saveNotificationSettingsBtn.addEventListener('click', function() {
        saveSettingsGroup('notificationSettingsForm', 'notification');
    });
    
    saveAdvancedSettingsBtn.addEventListener('click', function() {
        saveSettingsGroup('advancedSettingsForm', 'advanced');
    });
    
    // Functions
    function loadSettings() {
        // Load all settings by category
        fetch('/api/settings')
            .then(response => response.json())
            .then(categories => {
                // Populate form fields with existing settings
                for (const category in categories) {
                    categories[category].forEach(setting => {
                        const input = document.getElementById(setting.key);
                        if (input) {
                            if (input.type === 'checkbox') {
                                input.checked = setting.value === 'true';
                            } else if (input.type === 'radio') {
                                const radio = document.querySelector(`input[name="${input.name}"][value="${setting.value}"]`);
                                if (radio) {
                                    radio.checked = true;
                                }
                            } else {
                                input.value = setting.value;
                            }
                        }
                    });
                }
                
                // Apply settings that affect UI
                applyThemeSetting();
            })
            .catch(error => {
                console.error('Error loading settings:', error);
            });
    }
    
    function saveSettingsGroup(formId, category) {
        const form = document.getElementById(formId);
        const formData = new FormData(form);
        const settingsToSave = [];
        
        // Process form data
        for (const [key, value] of formData.entries()) {
            settingsToSave.push({
                key: key,
                value: value,
                category: category
            });
        }
        
        // Get checkbox values (unchecked checkboxes don't appear in FormData)
        const checkboxes = form.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            if (!checkbox.checked) {
                settingsToSave.push({
                    key: checkbox.name,
                    value: 'false',
                    category: category
                });
            }
        });
        
        // Save each setting
        const savePromises = settingsToSave.map(setting => {
            return fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(setting)
            }).then(response => {
                if (!response.ok) {
                    throw new Error(`Failed to save setting: ${setting.key}`);
                }
                return response.json();
            });
        });
        
        // Wait for all settings to be saved
        Promise.all(savePromises)
            .then(() => {
                // Show success message
                const alertHtml = `
                    <div class="alert alert-success alert-dismissible fade show" role="alert">
                        <i class="fas fa-check-circle me-2"></i> Settings saved successfully.
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                `;
                
                // Insert the alert before the form
                form.insertAdjacentHTML('beforebegin', alertHtml);
                
                // Apply settings that affect UI
                if (category === 'appearance') {
                    applyThemeSetting();
                }
            })
            .catch(error => {
                console.error('Error saving settings:', error);
                
                // Show error message
                const alertHtml = `
                    <div class="alert alert-danger alert-dismissible fade show" role="alert">
                        <i class="fas fa-exclamation-circle me-2"></i> Failed to save settings: ${error.message}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                `;
                
                // Insert the alert before the form
                form.insertAdjacentHTML('beforebegin', alertHtml);
            });
    }
    
    function applyThemeSetting() {
        // Get theme setting
        const darkThemeRadio = document.getElementById('theme_dark');
        const lightThemeRadio = document.getElementById('theme_light');
        
        if (darkThemeRadio && lightThemeRadio) {
            const isDarkTheme = darkThemeRadio.checked;
            
            // Apply theme
            document.documentElement.setAttribute('data-bs-theme', isDarkTheme ? 'dark' : 'light');
        }
    }
});