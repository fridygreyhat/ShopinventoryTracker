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
                                input.checked = setting.value === 'true' || setting.value === true;
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
});

// Global variables for subuser management
let currentPermissions = [];
let editingSubuserId = null;

// Helper function to get permission display names
function getPermissionDisplayName(permission) {
    const permissionNames = {
        'view_inventory': 'View Inventory',
        'edit_inventory': 'Edit Inventory',
        'delete_inventory': 'Delete Inventory',
        'view_sales': 'View Sales',
        'create_sales': 'Create Sales',
        'view_reports': 'View Reports',
        'export_data': 'Export Data',
        'manage_categories': 'Manage Categories',
        'view_financial': 'View Financial',
        'edit_financial': 'Edit Financial',
        'manage_settings': 'Manage Settings',
        'manage_users': 'Manage Users'
    };
    return permissionNames[permission] || permission;
}

function showAlert(message, type = 'info') {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    // Insert at the top of the content
    const container = document.querySelector('.container-fluid');
    container.insertBefore(alertDiv, container.firstChild);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Subuser Management Functions
async function loadSubusers() {
    try {
        showSubusersLoading(true);

        const response = await fetch('/api/subusers');
        if (!response.ok) {
            throw new Error('Failed to load subusers');
        }

        const subusers = await response.json();
        renderSubusers(subusers);

    } catch (error) {
        console.error('Error loading subusers:', error);
        showAlert('Failed to load subusers', 'danger');
    } finally {
        showSubusersLoading(false);
    }
}

function renderSubusers(subusers) {
    const container = document.getElementById('subusers-container');
    const noSubusersDiv = document.getElementById('no-subusers');

    if (subusers.length === 0) {
        container.innerHTML = '';
        noSubusersDiv.classList.remove('d-none');
        return;
    }

    noSubusersDiv.classList.add('d-none');

    container.innerHTML = subusers.map(subuser => createSubuserCard(subuser)).join('');
}

function createSubuserCard(subuser) {
    const permissionsList = subuser.permissions && subuser.permissions.length > 0 
        ? subuser.permissions.map(perm => getPermissionDisplayName(perm)).join(', ')
        : 'No permissions assigned';

    const statusBadge = subuser.is_active 
        ? '<span class="badge bg-success">Active</span>'
        : '<span class="badge bg-secondary">Inactive</span>';

    const safeName = subuser.name.replace(/'/g, "\\'");

    return `
        <div class="card mb-3">
            <div class="card-body">
                <div class="row align-items-center">
                    <div class="col-md-8">
                        <div class="d-flex align-items-center mb-2">
                            <h6 class="mb-0 me-3">${subuser.name}</h6>
                            ${statusBadge}
                        </div>
                        <div class="text-muted small mb-2">${subuser.email}</div>
                        <div class="small mb-2">
                            <strong>Permissions:</strong> 
                            <div class="mt-1">
                                ${subuser.permissions && subuser.permissions.length > 0 
                                    ? subuser.permissions.map(perm => `<span class="badge bg-light text-dark me-1">${getPermissionDisplayName(perm)}</span>`).join('')
                                    : '<span class="text-muted">No permissions assigned</span>'
                                }
                            </div>
                        </div>
                        <div class="text-muted small">
                            Created: ${new Date(subuser.created_at).toLocaleDateString()}
                            ${subuser.last_login ? ` | Last login: ${new Date(subuser.last_login).toLocaleDateString()}` : ''}
                        </div>
                    </div>
                    <div class="col-md-4 text-end">
                        <div class="btn-group">
                            <button type="button" class="btn btn-sm btn-outline-primary" onclick="editSubuser(${subuser.id})">
                                <i class="fas fa-edit"></i> Edit
                            </button>
                            <button type="button" class="btn btn-sm btn-outline-danger" onclick="confirmDeleteSubuser(${subuser.id}, '${safeName}')">
                                <i class="fas fa-trash"></i> Delete
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

async function loadPermissions() {
    try {
        const response = await fetch('/api/subusers/permissions');
        if (!response.ok) {
            throw new Error('Failed to load permissions');
        }

        const data = await response.json();
        console.log('Permissions loaded successfully:', data);

        currentPermissions = data.permissions || [];
        renderPermissions(data.permissions || [], data.descriptions || {});

    } catch (error) {
        console.error('Error loading permissions:', error);
        showAlert('Failed to load permissions', 'danger');

        // Fallback: render empty permissions container
        const container = document.getElementById('permissions-container');
        if (container) {
            container.innerHTML = '<div class="col-12"><p class="text-muted">Unable to load permissions at this time.</p></div>';
        }
    }
}

function renderPermissions(permissions, descriptions) {
    const container = document.getElementById('permissions-container');

    container.innerHTML = permissions.map(permission => `
        <div class="col-md-6 col-lg-4 mb-2">
            <div class="form-check">
                <input class="form-check-input" type="checkbox" value="${permission}" id="perm_${permission}">
                <label class="form-check-label small" for="perm_${permission}" title="${descriptions[permission] || permission}">
                    ${descriptions[permission] || permission}
                </label>
            </div>
        </div>
    `).join('');
}

async function handleSubuserSubmit(event) {
    event.preventDefault();

    const formData = {
        name: document.getElementById('subuserName').value.trim(),
        email: document.getElementById('subuserEmail').value.trim(),
        is_active: document.getElementById('subuserStatus').value === 'true',
        permissions: Array.from(document.querySelectorAll('#permissions-container input:checked')).map(cb => cb.value)
    };

    // Only include password if provided
    const passwordField = document.getElementById('subuserPassword');
    if (passwordField.value.trim()) {
        formData.password = passwordField.value;
    }

    if (!formData.name || !formData.email) {
        showAlert('Name and email are required', 'danger');
        return;
    }

    if (!editingSubuserId && !formData.password) {
        showAlert('Password is required for new subusers', 'danger');
        return;
    }

    try {
        const submitBtn = document.querySelector('#submit-btn-text');
        const submitSpinner = document.getElementById('submit-spinner');

        submitBtn.textContent = 'Saving...';
        submitSpinner.classList.remove('d-none');

        const url = editingSubuserId 
            ? `/api/subusers/${editingSubuserId}` 
            : '/api/subusers';

        const method = editingSubuserId ? 'PUT' : 'POST';

        console.log('Submitting subuser data:', formData);

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        const responseData = await response.json();
        console.log('Server response:', responseData);

        if (!response.ok) {
            throw new Error(responseData.error || 'Failed to save user');
        }

        // Close modal and refresh list
        const modal = bootstrap.Modal.getInstance(document.getElementById('addSubuserModal'));
        modal.hide();

        showAlert(editingSubuserId ? 'User updated successfully' : 'User added successfully', 'success');

        // Reload subusers to show the updated list
        await loadSubusers();

        // Reset form
        document.getElementById('subuserForm').reset();
        editingSubuserId = null;

    } catch (error) {
        console.error('Error saving subuser:', error);
        showAlert(error.message || 'Failed to save user', 'danger');
    } finally {
        // Reset button state
        const submitBtn = document.querySelector('#submit-btn-text');
        const submitSpinner = document.getElementById('submit-spinner');

        if (submitBtn) {
            submitBtn.textContent = editingSubuserId ? 'Update User' : 'Add User';
        }
        if (submitSpinner) {
            submitSpinner.classList.add('d-none');
        }
    }
}

function editSubuser(subuserId) {
    // Find the subuser data
    fetch(`/api/subusers`)
        .then(response => response.json())
        .then(subusers => {
            const subuser = subusers.find(s => s.id === subuserId);
            if (!subuser) return;

            editingSubuserId = subuserId;

            // Fill form
            document.getElementById('subuserId').value = subuser.id;
            document.getElementById('subuserName').value = subuser.name;
            document.getElementById('subuserEmail').value = subuser.email;
            document.getElementById('subuserPassword').value = ''; // Don't show existing password
            document.getElementById('subuserStatus').value = subuser.is_active.toString();

            // Update modal title
            document.getElementById('addSubuserModalLabel').textContent = 'Edit Subuser';

            // Mark permissions
            document.querySelectorAll('#permissions-container input[type="checkbox"]').forEach(cb => {
                cb.checked = subuser.permissions.includes(cb.value);
            });

            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('addSubuserModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error loading subuser:', error);
            showAlert('Failed to load subuser details', 'danger');
        });
}

function confirmDeleteSubuser(subuserId, subuserName) {
    document.getElementById('deleteSubuserName').textContent = subuserName;
    document.getElementById('confirmDeleteSubuser').dataset.subuserId = subuserId;

    const modal = new bootstrap.Modal(document.getElementById('deleteSubuserModal'));
    modal.show();
}

async function handleDeleteSubuser() {
    const subuserId = document.getElementById('confirmDeleteSubuser').dataset.subuserId;

    try {
        const response = await fetch(`/api/subusers/${subuserId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to delete subuser');
        }

        // Close modal and reload subusers
        const modal = bootstrap.Modal.getInstance(document.getElementById('deleteSubuserModal'));
        modal.hide();

        showAlert('Subuser deleted successfully', 'success');
        loadSubusers();

    } catch (error) {
        console.error('Error deleting subuser:', error);
        showAlert(error.message, 'danger');
    }
}

function showSubusersLoading(show) {
    const spinner = document.getElementById('loading-subusers');
    const container = document.getElementById('subusers-container');

    if (spinner) {
        if (show) {
            spinner.classList.remove('d-none');
        } else {
            spinner.classList.add('d-none');
        }
    }

    if (container) {
        if (show) {
            container.classList.add('d-none');
        } else {
            container.classList.remove('d-none');
        }
    }
}

// Reset modal when hidden
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('addSubuserModal');
    if (modal) {
        modal.addEventListener('hidden.bs.modal', function() {
            editingSubuserId = null;
            document.getElementById('subuserForm').reset();
            const subuserIdField = document.getElementById('subuserId');
            if (subuserIdField) {
                subuserIdField.value = '';
            }
            document.getElementById('addSubuserModalLabel').textContent = 'Add Team Member';

            // Uncheck all permissions
            document.querySelectorAll('#permissions-container input[type="checkbox"]').forEach(cb => {
                cb.checked = false;
            });

            // Reset button text
            const submitBtn = document.querySelector('#submit-btn-text');
            const submitSpinner = document.getElementById('submit-spinner');

            if (submitBtn) {
                submitBtn.textContent = 'Add User';
            }
            if (submitSpinner) {
                submitSpinner.classList.add('d-none');
            }
        });
    }
});

// Helper function to show alerts
function showAlert(message, type) {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    // Insert at top of page
    const container = document.querySelector('.container') || document.body;
    container.insertBefore(alertDiv, container.firstChild);

    // Auto dismiss after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}// Load all settings when page loads
    loadAllSettings();
});

// Test SMS function
function testSMS() {
    const phoneNumber = document.getElementById('notification_phone').value;

    if (!phoneNumber) {
        showAlert('Please enter a phone number first', 'warning');
        return;
    }

    // Show loading state
    const testButton = event.target;
    const originalText = testButton.innerHTML;
    testButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
    testButton.disabled = true;

    fetch('/api/notifications/test-sms', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            phone_number: phoneNumber,
            message: 'Test SMS from your Inventory Management System. SMS notifications are working correctly!'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Test SMS sent successfully!', 'success');
        } else {
            showAlert(data.error || 'Failed to send test SMS', 'danger');
        }
    })
    .catch(error => {
        console.error('Error sending test SMS:', error);
        showAlert('Error sending test SMS', 'danger');
    })
    .finally(() => {
        // Restore button state
        testButton.innerHTML = originalText;
        testButton.disabled = false;
    });
}

// Send low stock alert function
function sendLowStockAlert() {
    fetch('/api/notifications/send-low-stock-alert', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            let message = `Low stock alert sent! Found ${data.low_stock_count} low stock items.`;
            if (data.sms_sent) message += ' SMS sent.';
            if (data.email_sent) message += ' Email sent.';
            showAlert(message, 'success');
        } else {
            showAlert(`Failed to send alert: ${data.errors.join(', ')}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error sending low stock alert:', error);
        showAlert('Error sending low stock alert', 'danger');
    });
}