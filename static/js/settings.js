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
    if (saveGeneralSettingsBtn) {
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
    }

    if (saveAppearanceSettingsBtn) {
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
    }

    if (saveInventorySettingsBtn) {
        saveInventorySettingsBtn.addEventListener('click', function() {
            saveSettingsGroup('inventorySettingsForm', 'inventory');
        });
    }

    if (saveNotificationSettingsBtn) {
        saveNotificationSettingsBtn.addEventListener('click', function() {
            saveSettingsGroup('notificationSettingsForm', 'notification');
        });
    }

    if (saveAdvancedSettingsBtn) {
        saveAdvancedSettingsBtn.addEventListener('click', function() {
            saveSettingsGroup('advancedSettingsForm', 'advanced');
        });
    }

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
        if (!form) return Promise.reject(new Error('Form not found'));

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
                const callerFunction = arguments.callee.caller?.name;
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
                const callerFunction = arguments.callee.caller?.name;
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
        if (!form) return;

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
            })
            .catch(error => {
                console.error('Error saving settings before test:', error);
                showAlert('Failed to save settings before testing', 'danger');
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

// Initialize settings on tab show
document.addEventListener('DOMContentLoaded', function() {
    // Initialize subusers tab when clicked
    const userPermissionsTab = document.querySelector('a[href="#user-permissions"]');
    if (userPermissionsTab) {
        userPermissionsTab.addEventListener('shown.bs.tab', function() {
            console.log('User permissions tab shown, loading data...');
            // Add a small delay to ensure the tab is fully shown
            setTimeout(() => {
                loadSubusers();
                loadPermissions();
            }, 100);
        });

        // Also load if the tab is already active on page load
        if (userPermissionsTab.classList.contains('active')) {
            setTimeout(() => {
                loadSubusers();
                loadPermissions();
            }, 100);
        }
    }

    // Subuser form submission
    const subuserForm = document.getElementById('subuserForm');
    if (subuserForm) {
        subuserForm.addEventListener('submit', handleSubuserSubmit);
    }

    // Delete confirmation
    const confirmDeleteBtn = document.getElementById('confirmDeleteSubuser');
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', handleDeleteSubuser);
    }
});

// Global variables for subuser management
let currentEditingSubuserId = null;
let currentDeletingSubuserId = null;
let availablePermissions = [];

// Function to load subusers
function loadSubusers() {
    const loadingElement = document.getElementById('loading-subusers');
    const noSubusersElement = document.getElementById('no-subusers');
    const subusersContainer = document.getElementById('subusers-container');

    console.log('Loading subusers...');

    if (loadingElement) loadingElement.classList.remove('d-none');
    if (noSubusersElement) noSubusersElement.classList.add('d-none');
    if (subusersContainer) subusersContainer.innerHTML = '';

    fetch('/api/subusers', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache'
        },
        credentials: 'same-origin'
    })
        .then(response => {
            console.log('Subusers response status:', response.status);
            if (!response.ok) {
                if (response.status === 403) {
                    throw new Error('Access denied - insufficient permissions');
                } else if (response.status === 401) {
                    throw new Error('Authentication required - please login again');
                } else if (response.status >= 500) {
                    throw new Error('Server error - please try again later');
                } else {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
            }
            return response.json();
        })
        .then(data => {
            console.log('Subusers data loaded:', data);
            if (loadingElement) loadingElement.classList.add('d-none');

            if (!data || data.length === 0) {
                if (noSubusersElement) noSubusersElement.classList.remove('d-none');
            } else {
                renderSubusers(data);
            }
        })
        .catch(error => {
            console.error('Error loading subusers:', error);
            if (loadingElement) loadingElement.classList.add('d-none');

            // Show specific error message
            let errorMessage = 'Failed to load users';
            if (error.message.includes('Failed to fetch')) {
                errorMessage = 'Network error - please check your connection and try again';
            } else {
                errorMessage = error.message;
            }

            const errorHtml = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>${errorMessage}
                    <br><small class="mt-2 d-block">
                        <button class="btn btn-sm btn-outline-danger mt-2" onclick="loadSubusers()">
                            <i class="fas fa-redo me-1"></i>Try Again
                        </button>
                    </small>
                </div>
            `;
            if (subusersContainer) {
                subusersContainer.innerHTML = errorHtml;
            }
        });
}

// Function to load permissions
function loadPermissions() {
    const permissionsContainer = document.getElementById('permissions-container');

    // Show loading state
    if (permissionsContainer) {
        permissionsContainer.innerHTML = `
            <div class="col-12 text-center py-3">
                <div class="spinner-border spinner-border-sm text-primary" role="status">
                    <span class="visually-hidden">Loading permissions...</span>
                </div>
                <p class="mt-2 text-muted small">Loading permissions...</p>
            </div>
        `;
    }

    fetch('/api/subusers/permissions')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: Failed to load permissions`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Permissions loaded successfully:', data);
            if (data.success && data.permissions) {
                availablePermissions = data.permissions;
                renderPermissionsForm(data.permissions, data.descriptions || {});
            } else {
                throw new Error(data.error || 'Invalid permissions data received');
            }
        })
        .catch(error => {
            console.error('Error loading permissions:', error);
            showAlert('Failed to load permissions: ' + error.message, 'danger');

            // Show fallback permissions form
            if (permissionsContainer) {
                permissionsContainer.innerHTML = `
                    <div class="col-12">
                        <div class="alert alert-warning">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            Failed to load permissions. Please refresh the page and try again.
                        </div>
                    </div>
                `;
            }
        });
}

// Function to render permissions in the form
function renderPermissionsForm(permissions, descriptions) {
    const permissionsContainer = document.getElementById('permissions-container');
    if (!permissionsContainer) return;

    permissionsContainer.innerHTML = '';

    if (!permissions || permissions.length === 0) {
        permissionsContainer.innerHTML = `
            <div class="col-12">
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>No permissions available to assign.
                </div>
            </div>
        `;
        return;
    }

    permissions.forEach(permission => {
        const col = document.createElement('div');
        col.className = 'col-md-6 mb-2';

        const description = descriptions[permission] || permission.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

        col.innerHTML = `
            <div class="form-check">
                <input class="form-check-input" type="checkbox" value="${permission}" id="perm_${permission}" name="permissions">
                <label class="form-check-label" for="perm_${permission}">
                    ${description}
                </label>
            </div>
        `;

        permissionsContainer.appendChild(col);
    });
}

// Function to render subusers
function renderSubusers(subusers) {
    const container = document.getElementById('subusers-container');
    if (!container) return;

    container.innerHTML = '';

    if (!subusers || subusers.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-users fa-3x text-muted mb-3"></i>
                <h6 class="text-muted">No team members yet</h6>
                <p class="text-muted">Add team members to collaborate on your inventory management.</p>
            </div>
        `;
        return;
    }

    subusers.forEach(subuser => {
        const subuserCard = document.createElement('div');
        subuserCard.className = 'card mb-3';
        subuserCard.innerHTML = `
            <div class="card-body">
                <div class="row align-items-center">
                    <div class="col-md-8">
                        <h6 class="card-title mb-1">${subuser.name || 'Unknown User'}</h6>
                        <p class="card-text text-muted mb-1">${subuser.email || 'No email'}</p>
                        <span class="badge bg-${subuser.is_active ? 'success' : 'secondary'} me-2">
                            ${subuser.is_active ? 'Active' : 'Inactive'}
                        </span>
                        <small class="text-muted">${(subuser.permissions || []).length} permissions</small>
                    </div>
                    <div class="col-md-4 text-end">
                        <button type="button" class="btn btn-outline-primary btn-sm me-1" onclick="editSubuser(${subuser.id})">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                        <button type="button" class="btn btn-outline-danger btn-sm" onclick="deleteSubuser(${subuser.id}, '${(subuser.name || 'Unknown User').replace(/'/g, "\\'")}')">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </div>
                </div>
                <div class="mt-2">
                    <small class="text-muted">
                        <strong>Permissions:</strong> 
                        ${(subuser.permissions || []).length > 0 ? (subuser.permissions || []).join(', ') : 'No permissions assigned'}
                    </small>
                </div>
            </div>
        `;
        container.appendChild(subuserCard);
    });
}

// Function to handle subuser form submission
function handleSubuserSubmit(event) {
    event.preventDefault();

    // Get form elements with proper null checks
    const nameInput = document.getElementById('subuserName');
    const emailInput = document.getElementById('subuserEmail');
    const passwordInput = document.getElementById('subuserPassword');
    const statusInput = document.getElementById('subuserStatus');

    if (!nameInput || !emailInput || !passwordInput || !statusInput) {
        showAlert('Form elements not found. Please refresh the page.', 'danger');
        return;
    }

    const permissions = Array.from(document.querySelectorAll('input[name="permissions"]:checked')).map(cb => cb.value);

    const subuserData = {
        name: nameInput.value.trim(),
        email: emailInput.value.trim(),
        password: passwordInput.value,
        is_active: statusInput.value === 'true',
        permissions: permissions
    };

    console.log('Submitting subuser data:', subuserData);

    // Validate required fields
    if (!subuserData.name || !subuserData.email || (!currentEditingSubuserId && !subuserData.password)) {
        showAlert('Please fill in all required fields', 'danger');
        return;
    }

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(subuserData.email)) {
        showAlert('Please enter a valid email address', 'danger');
        return;
    }

    // Password validation for new users
    if (!currentEditingSubuserId && subuserData.password.length < 6) {
        showAlert('Password must be at least 6 characters long', 'danger');
        return;
    }

    // Show loading state
    const submitBtn = document.querySelector('#subuserForm button[type="submit"]');
    const submitBtnText = document.getElementById('submit-btn-text');
    const submitSpinner = document.getElementById('submit-spinner');

    if (submitBtn) submitBtn.disabled = true;
    if (submitBtnText) submitBtnText.textContent = currentEditingSubuserId ? 'Updating...' : 'Creating...';
    if (submitSpinner) submitSpinner.classList.remove('d-none');

    const url = currentEditingSubuserId ? `/api/subusers/${currentEditingSubuserId}` : '/api/subusers';
    const method = currentEditingSubuserId ? 'PUT' : 'POST';

    // Remove password from data if editing and password is empty
    if (currentEditingSubuserId && !subuserData.password) {
        delete subuserData.password;
    }

    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(subuserData)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('Subuser operation response:', data);

        if (data.success) {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('addSubuserModal'));
            if (modal) modal.hide();

            // Show success message
            showAlert(currentEditingSubuserId ? 'User updated successfully' : 'User created successfully', 'success');

            // Reload subusers
            loadSubusers();

            // Reset form
            resetSubuserForm();
        } else {
            throw new Error(data.error || 'Failed to save user');
        }
    })
    .catch(error => {
        console.error('Error saving subuser:', error);
        showAlert('Failed to save user: ' + error.message, 'danger');
    })
    .finally(() => {
        // Reset button state
        if (submitBtn) submitBtn.disabled = false;
        if (submitBtnText) submitBtnText.textContent = currentEditingSubuserId ? 'Update User' : 'Add User';
        if (submitSpinner) submitSpinner.classList.add('d-none');
    });
}

// Function to edit subuser
function editSubuser(subuserId) {
    currentEditingSubuserId = subuserId;

    // Find subuser data
    fetch(`/api/subusers/${subuserId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: Failed to load user data`);
            }
            return response.json();
        })
        .then(subuser => {
            // Fill form with subuser data
            const nameInput = document.getElementById('subuserName');
            const emailInput = document.getElementById('subuserEmail');
            const passwordInput = document.getElementById('subuserPassword');
            const statusInput = document.getElementById('subuserStatus');

            if (nameInput) nameInput.value = subuser.name || '';
            if (emailInput) emailInput.value = subuser.email || '';
            if (statusInput) statusInput.value = subuser.is_active ? 'true' : 'false';

            // Clear password field for editing and make it optional
            if (passwordInput) {
                passwordInput.value = '';
                passwordInput.required = false;
                passwordInput.placeholder = 'Leave blank to keep current password';
            }

            // Check permissions
            document.querySelectorAll('input[name="permissions"]').forEach(cb => {
                cb.checked = (subuser.permissions || []).includes(cb.value);
            });

            // Update modal title and button
            const modalLabel = document.getElementById('addSubuserModalLabel');
            const submitBtnText = document.getElementById('submit-btn-text');

            if (modalLabel) modalLabel.textContent = 'Edit User';
            if (submitBtnText) submitBtnText.textContent = 'Update User';

            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('addSubuserModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error loading subuser for editing:', error);
            showAlert('Failed to load user data: ' + error.message, 'danger');
        });
}

// Function to delete subuser
function deleteSubuser(subuserId, subuserName) {
    currentDeletingSubuserId = subuserId;

    // Update delete modal
    const deleteNameElement = document.getElementById('deleteSubuserName');
    if (deleteNameElement) {
        deleteNameElement.textContent = subuserName || 'Unknown User';
    }

    // Show delete modal
    const modal = new bootstrap.Modal(document.getElementById('deleteSubuserModal'));
    modal.show();
}

// Function to handle subuser deletion
function handleDeleteSubuser() {
    if (!currentDeletingSubuserId) return;

    const confirmBtn = document.getElementById('confirmDeleteSubuser');
    if (confirmBtn) {
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Deleting...';
    }

    fetch(`/api/subusers/${currentDeletingSubuserId}`, {
        method: 'DELETE'
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('deleteSubuserModal'));
            if (modal) modal.hide();

            // Show success message
            showAlert('User deleted successfully', 'success');

            // Reload subusers
            loadSubusers();
        } else {
            throw new Error(data.error || 'Failed to delete user');
        }
    })
    .catch(error => {
        console.error('Error deleting subuser:', error);
        showAlert('Failed to delete user: ' + error.message, 'danger');
    })
    .finally(() => {
        currentDeletingSubuserId = null;
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = 'Delete User';
        }
    });
}

// Function to reset subuser form
function resetSubuserForm() {
    currentEditingSubuserId = null;

    // Reset form fields
    const form = document.getElementById('subuserForm');
    if (form) form.reset();

    const passwordInput = document.getElementById('subuserPassword');
    if (passwordInput) {
        passwordInput.required = true;
        passwordInput.placeholder = 'Minimum 6 characters';
    }

    // Uncheck all permissions
    document.querySelectorAll('input[name="permissions"]').forEach(cb => {
        cb.checked = false;
    });

    // Reset modal title and button
    const modalLabel = document.getElementById('addSubuserModalLabel');
    const submitBtnText = document.getElementById('submit-btn-text');

    if (modalLabel) modalLabel.textContent = 'Add Team Member';
    if (submitBtnText) submitBtnText.textContent = 'Add User';
}

// Helper function to show alerts
function showAlert(message, type) {
    // Create alert element
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    // Find container for alerts
    const container = document.querySelector('.container') || document.body;
    container.insertBefore(alert, container.firstChild);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alert && alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

// Event listener for modal reset
document.addEventListener('hidden.bs.modal', function(event) {
    if (event.target.id === 'addSubuserModal') {
        resetSubuserForm();
    }
});