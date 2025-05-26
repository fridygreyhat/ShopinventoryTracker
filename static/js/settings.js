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
        const form = document.getElementById('generalSettingsForm');
        const settings = {
            company_name: form.company_name.value,
            currency_code: form.currency_code.value,
            timezone: form.timezone.value,
            default_language: form.default_language.value
        };

        // Save each setting individually
        Promise.all(Object.entries(settings).map(([key, value]) => {
            return fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    key: key,
                    value: value,
                    category: 'general'
                })
            }).then(response => response.json());
        }))
        .then(() => {
            // Show success message
            const alertHtml = `
                <div class="alert alert-success alert-dismissible fade show" role="alert">
                    <i class="fas fa-check-circle me-2"></i> General settings saved successfully.
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `;
            form.insertAdjacentHTML('beforebegin', alertHtml);

            // Reload page after short delay to reflect changes
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        })
        .catch(error => {
            console.error('Error saving general settings:', error);
            const alertHtml = `
                <div class="alert alert-danger alert-dismissible fade show" role="alert">
                    <i class="fas fa-exclamation-circle me-2"></i> Failed to save settings: ${error.message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `;
            form.insertAdjacentHTML('beforebegin', alertHtml);
        });
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

                // Initialize enhanced theme selection
                initEnhancedThemeSelection();
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

    function initEnhancedThemeSelection() {
        const themeCards = document.querySelectorAll('.theme-card');
        const livePreview = document.getElementById('livePreview');

        // Add event listeners to theme cards
        themeCards.forEach(card => {
            const themeValue = card.getAttribute('data-theme');
            const radioInput = card.querySelector('input[type="radio"]');

            // Click handler
            card.addEventListener('click', function() {
                selectTheme(themeValue, card);
            });

            // Keyboard handler
            card.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    selectTheme(themeValue, card);
                }
            });

            // Update active state on load
            if (radioInput && radioInput.checked) {
                updateActiveThemeCard(card);
                updateLivePreview(themeValue);
            }
        });

        // Initialize live preview with current theme
        const currentTheme = document.querySelector('input[name="theme"]:checked');
        if (currentTheme) {
            updateLivePreview(currentTheme.value);
        }
    }

    function selectTheme(themeValue, cardElement) {
        // Update radio button
        const radioInput = document.getElementById(`theme_${themeValue}`);
        if (radioInput) {
            radioInput.checked = true;
        }

        // Update active states
        document.querySelectorAll('.theme-card').forEach(card => {
            card.classList.remove('active');
        });
        cardElement.classList.add('active');

        // Apply theme immediately using global setTheme function
        if (window.setTheme) {
            window.setTheme(themeValue);
        }

        // Update live preview
        updateLivePreview(themeValue);

        // Announce change for screen readers
        announceThemeChange(themeValue);
    }

    function updateActiveThemeCard(activeCard) {
        document.querySelectorAll('.theme-card').forEach(card => {
            card.classList.remove('active');
        });
        activeCard.classList.add('active');
    }

    function updateLivePreview(themeValue) {
        const livePreview = document.getElementById('livePreview');
        if (!livePreview) return;

        // Apply theme to live preview
        livePreview.setAttribute('data-theme-preview', themeValue);

        // Get theme colors based on theme value
        const themeColors = getThemeColors(themeValue);

        // Update CSS custom properties for the preview
        const headerSection = livePreview.querySelector('.preview-header-section');
        const menuItems = livePreview.querySelectorAll('.preview-menu-item.active');
        const primaryBtns = livePreview.querySelectorAll('.preview-btn.primary');
        const secondaryBtns = livePreview.querySelectorAll('.preview-btn.secondary');

        if (headerSection) {
            headerSection.style.background = themeColors.primary;
        }

        menuItems.forEach(item => {
            item.style.background = themeColors.primary;
        });

        primaryBtns.forEach(btn => {
            btn.style.background = themeColors.primary;
        });

        secondaryBtns.forEach(btn => {
            btn.style.color = themeColors.primary;
            btn.style.borderColor = themeColors.primary;
        });
    }

    function getThemeColors(themeValue) {
        const themeColorMap = {
            tanzanite: {
                primary: '#4C50C5',
                secondary: '#41C1E0',
                accent: '#FF7950'
            },
            forest: {
                primary: '#2E7D32',
                secondary: '#81C784',
                accent: '#FF8F00'
            },
            ocean: {
                primary: '#0277BD',
                secondary: '#4FC3F7',
                accent: '#FF8A65'
            },
            sunset: {
                primary: '#E65100',
                secondary: '#FF9800',
                accent: '#5E35B1'
            },
            dark: {
                primary: '#7986CB',
                secondary: '#5C6BC0',
                accent: '#FF8A65'
            }
        };

        return themeColorMap[themeValue] || themeColorMap.tanzanite;
    }

    function announceThemeChange(themeValue) {
        // Create a live region for screen readers
        let announcer = document.getElementById('theme-announcer');
        if (!announcer) {
            announcer = document.createElement('div');
            announcer.id = 'theme-announcer';
            announcer.setAttribute('aria-live', 'polite');
            announcer.setAttribute('aria-atomic', 'true');
            announcer.style.position = 'absolute';
            announcer.style.left = '-10000px';
            announcer.style.width = '1px';
            announcer.style.height = '1px';
            announcer.style.overflow = 'hidden';
            document.body.appendChild(announcer);
        }

        const themeNames = {
            tanzanite: 'Tanzanite',
            forest: 'Forest',
            ocean: 'Ocean',
            sunset: 'Sunset',
            dark: 'Dark'
        };

        announcer.textContent = `${themeNames[themeValue]} theme selected`;
    }
});