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

// Initialize settings on tab show
document.addEventListener('DOMContentLoaded', function() {
    // Initialize subusers tab when clicked
    const userPermissionsTab = document.querySelector('a[href="#user-permissions"]');
    if (userPermissionsTab) {
        userPermissionsTab.addEventListener('shown.bs.tab', function() {
            console.log('User permissions tab shown, loading data...');
            loadSubusers();
            loadPermissions();
        });

        // Also load if the tab is already active on page load
        if (userPermissionsTab.classList.contains('active')) {
            loadSubusers();
            loadPermissions();
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

    // Theme switching functionality
    initializeThemes();

    // Initialize general settings
    loadGeneralSettings();

    // Initialize notification settings
    loadNotificationSettings();

    // Initialize advanced settings
    loadAdvancedSettings();
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

    if (loadingElement) loadingElement.classList.remove('d-none');
    if (noSubusersElement) noSubusersElement.classList.add('d-none');
    if (subusersContainer) subusersContainer.innerHTML = '';

    fetch('/api/subusers')
        .then(response => response.json())
        .then(data => {
            if (loadingElement) loadingElement.classList.add('d-none');

            if (data.length === 0) {
                if (noSubusersElement) noSubusersElement.classList.remove('d-none');
            } else {
                renderSubusers(data);
            }
        })
        .catch(error => {
            console.error('Error loading subusers:', error);
            if (loadingElement) loadingElement.classList.add('d-none');
            if (noSubusersElement) noSubusersElement.classList.remove('d-none');
        });
}

// Function to load permissions
function loadPermissions() {
    fetch('/api/subusers/permissions')
        .then(response => response.json())
        .then(data => {
            console.log('Permissions loaded successfully:', data);
            if (data.success && data.permissions) {
                availablePermissions = data.permissions;
                renderPermissionsForm(data.permissions, data.descriptions || {});
            } else {
                console.error('Failed to load permissions:', data);
                showAlert('Failed to load permissions', 'danger');
            }
        })
        .catch(error => {
            console.error('Error loading permissions:', error);
            showAlert('Failed to load permissions', 'danger');
        });
}

// Function to render permissions in the form
function renderPermissionsForm(permissions, descriptions) {
    const permissionsContainer = document.getElementById('permissions-container');
    if (!permissionsContainer) return;

    permissionsContainer.innerHTML = '';

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

    subusers.forEach(subuser => {
        const subuserCard = document.createElement('div');
        subuserCard.className = 'card mb-3';
        subuserCard.innerHTML = `
            <div class="card-body">
                <div class="row align-items-center">
                    <div class="col-md-8">
                        <h6 class="card-title mb-1">${subuser.name}</h6>
                        <p class="card-text text-muted mb-1">${subuser.email}</p>
                        <span class="badge bg-${subuser.is_active ? 'success' : 'secondary'} me-2">
                            ${subuser.is_active ? 'Active' : 'Inactive'}
                        </span>
                        <small class="text-muted">${subuser.permissions.length} permissions</small>
                    </div>
                    <div class="col-md-4 text-end">
                        <button type="button" class="btn btn-outline-primary btn-sm me-1" onclick="editSubuser(${subuser.id})">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                        <button type="button" class="btn btn-outline-danger btn-sm" onclick="deleteSubuser(${subuser.id}, '${subuser.name}')">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </div>
                </div>
                <div class="mt-2">
                    <small class="text-muted">
                        <strong>Permissions:</strong> 
                        ${subuser.permissions.length > 0 ? subuser.permissions.join(', ') : 'No permissions assigned'}
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

    const formData = new FormData(event.target);
    const permissions = Array.from(document.querySelectorAll('input[name="permissions"]:checked')).map(cb => cb.value);

    const subuserData = {
        name: formData.get('subuserName') || document.getElementById('subuserName').value,
        email: formData.get('subuserEmail') || document.getElementById('subuserEmail').value,
        password: formData.get('subuserPassword') || document.getElementById('subuserPassword').value,
        is_active: formData.get('subuserStatus') === 'true' || document.getElementById('subuserStatus').value === 'true',
        permissions: permissions
    };

    console.log('Submitting subuser data:', subuserData);

    // Validate required fields
    if (!subuserData.name || !subuserData.email || !subuserData.password) {
        showAlert('Please fill in all required fields', 'danger');
        return;
    }

    // Show loading state
    const submitBtn = document.querySelector('#submit-btn-text');
    const submitSpinner = document.getElementById('submit-spinner');

    if (submitBtn) submitBtn.textContent = currentEditingSubuserId ? 'Updating...' : 'Creating...';
    if (submitSpinner) submitSpinner.classList.remove('d-none');

    const url = currentEditingSubuserId ? `/api/subusers/${currentEditingSubuserId}` : '/api/subusers';
    const method = currentEditingSubuserId ? 'PUT' : 'POST';

    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(subuserData)
    })
    .then(response => response.json())
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
            showAlert(data.error || 'Failed to save user', 'danger');
        }
    })
    .catch(error => {
        console.error('Error saving subuser:', error);
        showAlert('Failed to save user', 'danger');
    })
    .finally(() => {
        // Reset button state
        if (submitBtn) submitBtn.textContent = currentEditingSubuserId ? 'Update User' : 'Add User';
        if (submitSpinner) submitSpinner.classList.add('d-none');
    });
}

// Function to edit subuser
function editSubuser(subuserId) {
    currentEditingSubuserId = subuserId;

    // Find subuser data
    fetch(`/api/subusers/${subuserId}`)
        .then(response => response.json())
        .then(subuser => {
            // Fill form with subuser data
            document.getElementById('subuserName').value = subuser.name;
            document.getElementById('subuserEmail').value = subuser.email;
            document.getElementById('subuserStatus').value = subuser.is_active.toString();

            // Clear password field for editing
            document.getElementById('subuserPassword').value = '';
            document.getElementById('subuserPassword').required = false;

            // Check permissions
            document.querySelectorAll('input[name="permissions"]').forEach(cb => {
                cb.checked = subuser.permissions.includes(cb.value);
            });

            // Update modal title and button
            document.getElementById('addSubuserModalLabel').textContent = 'Edit User';
            document.getElementById('submit-btn-text').textContent = 'Update User';

            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('addSubuserModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error loading subuser for editing:', error);
            showAlert('Failed to load user data', 'danger');
        });
}

// Function to delete subuser
function deleteSubuser(subuserId, subuserName) {
    currentDeletingSubuserId = subuserId;

    // Update delete modal
    document.getElementById('deleteSubuserName').textContent = subuserName;

    // Show delete modal
    const modal = new bootstrap.Modal(document.getElementById('deleteSubuserModal'));
    modal.show();
}

// Function to handle subuser deletion
function handleDeleteSubuser() {
    if (!currentDeletingSubuserId) return;

    fetch(`/api/subusers/${currentDeletingSubuserId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
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
            showAlert(data.error || 'Failed to delete user', 'danger');
        }
    })
    .catch(error => {
        console.error('Error deleting subuser:', error);
        showAlert('Failed to delete user', 'danger');
    })
    .finally(() => {
        currentDeletingSubuserId = null;
    });
}

// Function to reset subuser form
function resetSubuserForm() {
    currentEditingSubuserId = null;

    // Reset form fields
    document.getElementById('subuserForm').reset();
    document.getElementById('subuserPassword').required = true;

    // Uncheck all permissions
    document.querySelectorAll('input[name="permissions"]').forEach(cb => {
        cb.checked = false;
    });

    // Reset modal title and button
    document.getElementById('addSubuserModalLabel').textContent = 'Add Team Member';
    document.getElementById('submit-btn-text').textContent = 'Add User';
}

// Initialize theme functionality
function initializeThemes() {
    // Theme selection handling
    const themeCards = document.querySelectorAll('.theme-card');
    const livePreview = document.getElementById('livePreview');

    themeCards.forEach(card => {
        card.addEventListener('click', function() {
            const theme = this.dataset.theme;
            const radio = this.querySelector('input[type="radio"]');

            // Update radio selection
            radio.checked = true;

            // Update visual selection
            themeCards.forEach(c => c.classList.remove('selected'));
            this.classList.add('selected');

            // Update live preview
            if (livePreview) {
                livePreview.className = `live-preview-container theme-${theme}`;
            }
        });
    });

    // Appearance settings form submission
    const saveAppearanceBtn = document.getElementById('saveAppearanceSettings');
    if (saveAppearanceBtn) {
        saveAppearanceBtn.addEventListener('click', function() {
            const selectedTheme = document.querySelector('input[name="theme"]:checked').value;
            const itemsPerPage = document.getElementById('items_per_page').value;
            const dateFormat = document.getElementById('date_format').value;

            const appearanceData = {
                theme: selectedTheme,
                itemsPerPage: itemsPerPage,
                dateFormat: dateFormat
            };

            fetch('/api/settings/appearance', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(appearanceData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert('Appearance settings saved successfully', 'success');
                    // Apply theme immediately
                    document.body.setAttribute('data-theme-value', selectedTheme);
                } else {
                    showAlert('Failed to save appearance settings', 'danger');
                }
            })
            .catch(error => {
                console.error('Error saving appearance settings:', error);
                showAlert('Failed to save appearance settings', 'danger');
            });
        });
    }
}

// Load general settings
function loadGeneralSettings() {
    const saveGeneralBtn = document.getElementById('saveGeneralSettings');
    if (saveGeneralBtn) {
        saveGeneralBtn.addEventListener('click', function() {
            const formData = {
                company_name: document.getElementById('company_name').value,
                currency_code: document.getElementById('currency_code').value,
                timezone: document.getElementById('timezone').value,
                default_language: document.getElementById('default_language').value
            };

            // Save each setting
            const promises = Object.entries(formData).map(([key, value]) => {
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
                });
            });

            Promise.all(promises)
                .then(() => {
                    showAlert('General settings saved successfully', 'success');
                })
                .catch(error => {
                    console.error('Error saving general settings:', error);
                    showAlert('Failed to save general settings', 'danger');
                });
        });
    }
}

// Load notification settings
function loadNotificationSettings() {
    const saveNotificationBtn = document.getElementById('saveNotificationSettings');
    const testNotificationBtn = document.getElementById('testNotifications');

    if (saveNotificationBtn) {
        saveNotificationBtn.addEventListener('click', function() {
            const formData = {
                email_notifications_enabled: document.getElementById('email_notifications_enabled').checked,
                sms_notifications_enabled: document.getElementById('sms_notifications_enabled').checked,
                enable_price_change_alerts: document.getElementById('enable_price_change_alerts').checked,
                notification_email: document.getElementById('notification_email').value,
                sender_email: document.getElementById('sender_email').value,
                notification_phone: document.getElementById('notification_phone').value,
                notification_low_stock_threshold: document.getElementById('notification_low_stock_threshold').value,
                notification_frequency: document.getElementById('notification_frequency').value
            };

            // Save each setting
            const promises = Object.entries(formData).map(([key, value]) => {
                return fetch('/api/settings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        key: key,
                        value: typeof value === 'boolean' ? value.toString() : value,
                        category: 'notifications'
                    })
                });
            });

            Promise.all(promises)
                .then(() => {
                    showAlert('Notification settings saved successfully', 'success');
                })
                .catch(error => {
                    console.error('Error saving notification settings:', error);
                    showAlert('Failed to save notification settings', 'danger');
                });
        });
    }

    if (testNotificationBtn) {
        testNotificationBtn.addEventListener('click', function() {
            fetch('/api/notifications/test', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert('Test notifications sent successfully', 'success');
                } else {
                    showAlert('Failed to send test notifications', 'danger');
                }
            })
            .catch(error => {
                console.error('Error sending test notifications:', error);
                showAlert('Failed to send test notifications', 'danger');
            });
        });
    }
}

// Load advanced settings
function loadAdvancedSettings() {
    const saveAdvancedBtn = document.getElementById('saveAdvancedSettings');
    if (saveAdvancedBtn) {
        saveAdvancedBtn.addEventListener('click', function() {
            const formData = {
                enable_debug_mode: document.getElementById('enable_debug_mode').checked,
                data_backup_schedule: document.getElementById('data_backup_schedule').value,
                enable_api_access: document.getElementById('enable_api_access').checked
            };

            // Save each setting
            const promises = Object.entries(formData).map(([key, value]) => {
                return fetch('/api/settings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        key: key,
                        value: typeof value === 'boolean' ? value.toString() : value,
                        category: 'advanced'
                    })
                });
            });

            Promise.all(promises)
                .then(() => {
                    showAlert('Advanced settings saved successfully', 'success');
                })
                .catch(error => {
                    console.error('Error saving advanced settings:', error);
                    showAlert('Failed to save advanced settings', 'danger');
                });
        });
    }
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