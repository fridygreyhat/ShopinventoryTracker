document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const saveGeneralSettingsBtn = document.getElementById('saveGeneralSettings');
    const saveAppearanceSettingsBtn = document.getElementById('saveAppearanceSettings');
    const saveInventorySettingsBtn = document.getElementById('saveInventorySettings');
    const saveNotificationSettingsBtn = document.getElementById('saveNotificationSettings');
    const saveAdvancedSettingsBtn = document.getElementById('saveAdvancedSettings');
    const testNotificationsBtn = document.getElementById('testNotifications');
    
    // Initialize settings
    loadSettings();
    
    // Event Listeners
    saveGeneralSettingsBtn.addEventListener('click', function() {
        saveSettingsGroup('generalSettingsForm', 'general');
    });
    
    saveAppearanceSettingsBtn.addEventListener('click', function() {
        // Save appearance settings using the dedicated API endpoint
        const form = document.getElementById('appearanceSettingsForm');
        const formData = new FormData(form);
        
        const theme = formData.get('theme');
        const itemsPerPage = formData.get('items_per_page');
        const dateFormat = formData.get('date_format');
        
        // Call the appearance settings API
        fetch('/api/settings/appearance', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                theme: theme,
                itemsPerPage: itemsPerPage,
                dateFormat: dateFormat
            })
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                // Apply the theme immediately
                if (theme) {
                    // Use the global setTheme function from theme-switcher.js
                    setTheme(theme);
                }
                
                // Show success message
                const alertHtml = `
                    <div class="alert alert-success alert-dismissible fade show" role="alert">
                        <i class="fas fa-check-circle me-2"></i> Appearance settings saved successfully.
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                `;
                form.insertAdjacentHTML('beforebegin', alertHtml);
            } else {
                throw new Error(result.error || 'Failed to save appearance settings');
            }
        })
        .catch(error => {
            console.error('Error saving appearance settings:', error);
            
            // Show error message
            const alertHtml = `
                <div class="alert alert-danger alert-dismissible fade show" role="alert">
                    <i class="fas fa-exclamation-circle me-2"></i> Failed to save appearance settings: ${error.message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `;
            form.insertAdjacentHTML('beforebegin', alertHtml);
        });
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
    
    // Test notifications button
    if (testNotificationsBtn) {
        testNotificationsBtn.addEventListener('click', function() {
            testNotifications();
        });
    }
    
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
        
        // Return a promise that resolves when all settings are saved
        return Promise.all(savePromises)
            .then(() => {
                // Show success message (unless this is being called from the test function)
                const callerFunction = arguments.callee.caller.name;
                if (callerFunction !== 'testNotifications') {
                    const alertHtml = `
                        <div class="alert alert-success alert-dismissible fade show" role="alert">
                            <i class="fas fa-check-circle me-2"></i> Settings saved successfully.
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>
                    `;
                    
                    // Insert the alert before the form
                    form.insertAdjacentHTML('beforebegin', alertHtml);
                }
                
                // Apply settings that affect UI
                if (category === 'appearance') {
                    applyThemeSetting();
                }
                
                // Return success for promise chaining
                return true;
            })
            .catch(error => {
                console.error('Error saving settings:', error);
                
                // Show error message (unless this is being called from the test function)
                const callerFunction = arguments.callee.caller.name;
                if (callerFunction !== 'testNotifications') {
                    const alertHtml = `
                        <div class="alert alert-danger alert-dismissible fade show" role="alert">
                            <i class="fas fa-exclamation-circle me-2"></i> Failed to save settings: ${error.message}
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>
                    `;
                    
                    // Insert the alert before the form
                    form.insertAdjacentHTML('beforebegin', alertHtml);
                }
                
                // Re-throw the error for promise chaining
                throw error;
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
    
    function testNotifications() {
        // Get the form with notification settings
        const form = document.getElementById('notificationSettingsForm');
        
        // First save the current settings to ensure we're testing with the latest configuration
        saveSettingsGroup('notificationSettingsForm', 'notification')
            .then(() => {
                // Show loading state on the button
                const testButton = document.getElementById('testNotifications');
                const originalText = testButton.innerHTML;
                testButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
                testButton.disabled = true;
                
                // Call the test notifications endpoint
                fetch('/api/notifications/test', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.json())
                .then(result => {
                    // Reset button state
                    testButton.innerHTML = originalText;
                    testButton.disabled = false;
                    
                    // Create appropriate alert based on the result
                    let alertClass = 'alert-info';
                    let alertIcon = 'info-circle';
                    let alertTitle = 'Notification Test Results';
                    let alertContent = '';
                    
                    if (result.success) {
                        alertClass = 'alert-success';
                        alertIcon = 'check-circle';
                        alertTitle = 'Notifications Test Successful';
                        
                        // Build success message
                        if (result.email_sent && result.sms_sent) {
                            alertContent = 'Both email and SMS notifications were sent successfully.';
                        } else if (result.email_sent) {
                            alertContent = 'Email notification was sent successfully.';
                        } else if (result.sms_sent) {
                            alertContent = 'SMS notification was sent successfully.';
                        } else {
                            alertContent = 'Test completed but no notifications were sent. This could be because both notification types are disabled or there are no low stock items.';
                        }
                    } else {
                        alertClass = 'alert-danger';
                        alertIcon = 'exclamation-circle';
                        alertTitle = 'Notification Test Failed';
                        
                        // Build error message
                        alertContent = 'Failed to send test notifications. Please check your settings and try again.<br>';
                        
                        if (result.errors && result.errors.length > 0) {
                            alertContent += '<ul class="mt-2 mb-0">';
                            result.errors.forEach(error => {
                                alertContent += `<li>${error}</li>`;
                            });
                            alertContent += '</ul>';
                        }
                    }
                    
                    // Create and show the alert
                    const alertHtml = `
                        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                            <h5 class="alert-heading"><i class="fas fa-${alertIcon} me-2"></i> ${alertTitle}</h5>
                            <p>${alertContent}</p>
                            <hr>
                            <p class="mb-0">
                                <small>
                                    <strong>Low Stock Items:</strong> ${result.low_stock_count || 0} items
                                </small>
                            </p>
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>
                    `;
                    
                    // Insert the alert before the form
                    form.insertAdjacentHTML('beforebegin', alertHtml);
                })
                .catch(error => {
                    // Reset button state
                    testButton.innerHTML = originalText;
                    testButton.disabled = false;
                    
                    // Show error message
                    const alertHtml = `
                        <div class="alert alert-danger alert-dismissible fade show" role="alert">
                            <i class="fas fa-exclamation-circle me-2"></i> Error testing notifications: ${error.message}
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>
                    `;
                    
                    // Insert the alert before the form
                    form.insertAdjacentHTML('beforebegin', alertHtml);
                });
            });
    }
});