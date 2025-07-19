/**
 * Categories Management JavaScript
 * Handles CRUD operations for categories and subcategories
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize page
    loadCategories();
    loadParentCategories();

    // Event listeners
    document.getElementById('categoryForm').addEventListener('submit', handleCategorySubmit);
    document.getElementById('subcategoryForm').addEventListener('submit', handleSubcategorySubmit);
});

let categories = [];
let editingCategory = null;
let editingSubcategory = null;

// Fix categories loading
function loadCategories() {
    // Show loading state
    const categoriesTableBody = document.getElementById('categoriesTableBody');
    if (categoriesTableBody) {
        categoriesTableBody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-5">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading categories...</span>
                    </div>
                    <p class="mt-2 text-muted">Loading categories...</p>
                </td>
            </tr>
        `;
    }

    fetch('/api/categories', {
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then(response => {
            if (!response.ok) {
                if (response.status === 401) {
                    showAlert('Please log in to view categories', 'warning');
                    return [];
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(categoriesData => {
            console.log('Categories loaded:', categoriesData);
            // Store globally for other functions
            categories = categoriesData || [];
            displayCategories(categoriesData);
            updateCategoryStats(categoriesData);
        })
        .catch(error => {
            console.error('Error loading categories:', error);
            showAlert('Failed to load categories: ' + error.message, 'danger');
            // Show error state
            const categoriesTableBody = document.getElementById('categoriesTableBody');
            if (categoriesTableBody) {
                categoriesTableBody.innerHTML = `
                    <tr>
                        <td colspan="8" class="text-center py-5">
                            <div class="alert alert-danger">
                                <i class="fas fa-exclamation-triangle fa-3x mb-3"></i>
                                <h4>Error Loading Categories</h4>
                                <p>Unable to load categories: ${error.message}</p>
                                <button class="btn btn-primary" onclick="loadCategories()">
                                    <i class="fas fa-refresh me-2"></i>Try Again
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            }
        });
}

function displayCategories(categories) {
    const categoriesTableBody = document.getElementById('categoriesTableBody');
    if (!categoriesTableBody) {
        console.warn('Categories table body not found');
        return;
    }

    if (!categories || categories.length === 0) {
        categoriesTableBody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-5">
                    <i class="fas fa-folder-open fa-3x mb-3 text-muted"></i>
                    <h4>No categories found</h4>
                    <p class="text-muted">Create your first category to organize your products</p>
                    <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#categoryModal">
                        <i class="fas fa-plus me-2"></i>Add Category
                    </button>
                </td>
            </tr>
        `;
        return;
    }

    let html = '';
    
    // First, add all parent categories
    categories.forEach(category => {
        if (!category.parent_id) {
            const directItemCount = category.item_count || 0;
            const totalItemCount = category.total_item_count || 0;
            const statusBadge = category.is_active ? 
                '<span class="badge bg-success">Active</span>' : 
                '<span class="badge bg-danger">Inactive</span>';

            html += `
                <tr class="table-primary">
                    <td><strong>${category.id}</strong></td>
                    <td>
                        <div class="d-flex align-items-center">
                            <i class="fas fa-folder text-primary me-2"></i>
                            <strong>${escapeHtml(category.name)}</strong>
                        </div>
                    </td>
                    <td class="text-muted small">${escapeHtml(category.description || 'No description')}</td>
                    <td><span class="badge bg-secondary">Main Category</span></td>
                    <td><span class="badge bg-primary">${directItemCount}</span></td>
                    <td><span class="badge bg-success">${totalItemCount}</span></td>
                    <td>${statusBadge}</td>
                    <td>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary btn-sm" onclick="editCategory(${category.id})" title="Edit Category">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-outline-info btn-sm" onclick="addSubcategory(${category.id})" title="Add Subcategory">
                                <i class="fas fa-plus"></i>
                            </button>
                            <button class="btn btn-outline-danger btn-sm" onclick="deleteCategory(${category.id})" title="Delete Category">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;

            // Add subcategories right after their parent
            if (category.subcategories && category.subcategories.length > 0) {
                category.subcategories.forEach(subcategory => {
                    const subItemCount = subcategory.item_count || 0;
                    const subTotalCount = subcategory.total_item_count || 0;
                    const subStatusBadge = subcategory.is_active ? 
                        '<span class="badge bg-success">Active</span>' : 
                        '<span class="badge bg-danger">Inactive</span>';

                    html += `
                        <tr>
                            <td class="ps-4">${subcategory.id}</td>
                            <td class="ps-4">
                                <div class="d-flex align-items-center">
                                    <i class="fas fa-folder-open text-secondary me-2"></i>
                                    ${escapeHtml(subcategory.name)}
                                </div>
                            </td>
                            <td class="text-muted small">${escapeHtml(subcategory.description || 'No description')}</td>
                            <td>
                                <div class="d-flex align-items-center">
                                    <i class="fas fa-arrow-right text-muted me-1"></i>
                                    <small class="text-muted">${escapeHtml(category.name)}</small>
                                </div>
                            </td>
                            <td><span class="badge bg-primary">${subItemCount}</span></td>
                            <td><span class="badge bg-success">${subTotalCount}</span></td>
                            <td>${subStatusBadge}</td>
                            <td>
                                <div class="btn-group btn-group-sm">
                                    <button class="btn btn-outline-primary btn-sm" onclick="editSubcategory(${subcategory.id})" title="Edit Subcategory">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="btn btn-outline-danger btn-sm" onclick="deleteSubcategory(${subcategory.id})" title="Delete Subcategory">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `;
                });
            }
        }
    });

    categoriesTableBody.innerHTML = html;
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text ? text.replace(/[&<>"']/g, function(m) { return map[m]; }) : '';
}

function updateCategoryStats(categories) {
    if (!categories || categories.length === 0) {
        document.getElementById('categoryStats').style.display = 'none';
        return;
    }

    let totalCategories = categories.length;
    let totalSubcategories = 0;
    let totalItems = 0;

    categories.forEach(category => {
        if (category.subcategories) {
            totalSubcategories += category.subcategories.length;
        }
        totalItems += category.total_item_count || 0;
    });

    const avgItemsPerCategory = totalCategories > 0 ? Math.round(totalItems / totalCategories) : 0;

    // Update stats display
    document.getElementById('totalCategories').textContent = totalCategories;
    document.getElementById('totalSubcategories').textContent = totalSubcategories;
    document.getElementById('totalItems').textContent = totalItems;
    document.getElementById('avgItemsPerCategory').textContent = avgItemsPerCategory;

    // Show stats section
    document.getElementById('categoryStats').style.display = 'block';
}

/**
 * Render categories in the UI
 */
/*
function renderCategories() {
    const container = document.getElementById('categories-container');

    if (!categories || categories.length === 0) {
        container.innerHTML = `
            <div class="col-12">
                <div class="card text-center p-5">
                    <div class="card-body">
                        <i class="fas fa-folder-open fa-3x text-muted mb-3"></i>
                        <h4 class="text-muted">No Categories Found</h4>
                        <p class="text-muted">Start by creating your first product category.</p>
                        <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#categoryModal">
                            <i class="fas fa-plus me-2"></i>Add Category
                        </button>
                    </div>
                </div>
            </div>
        `;
        return;
    }

    // Categories already come with subcategories from the API
    container.innerHTML = categories.map(category => createCategoryCard(category)).join('');
}
*/

/**
 * Create HTML for a category card
 */
function createCategoryCard(category) {
    const subcategories = category.subcategories || [];
    const subcategoriesHtml = subcategories.length > 0 
        ? subcategories.map(sub => `
            <div class="subcategory-item d-flex justify-content-between align-items-center mb-1">
                <span class="text-muted small">
                    <i class="fas fa-chevron-right me-1"></i>${sub.name}
                </span>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary btn-sm" onclick="editSubcategory(${sub.id})" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-outline-danger btn-sm" onclick="deleteSubcategory(${sub.id})" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('')
        : '<p class="text-muted small">No subcategories</p>';

    return `
        <div class="col-md-6 col-lg-4 mb-4">
            <div class="card h-100 category-card" style="border-left: 4px solid ${category.color || '#007bff'}">
                <div class="card-header d-flex justify-content-between align-items-center" style="background-color: ${category.color || '#007bff'}10">
                    <div class="d-flex align-items-center">
                        <i class="${category.icon || 'fas fa-folder'} me-2" style="color: ${category.color || '#007bff'}"></i>
                        <h5 class="mb-0">${category.name}</h5>
                    </div>
                    <div class="dropdown">
                        <button class="btn btn-sm btn-outline-secondary" type="button" data-bs-toggle="dropdown">
                            <i class="fas fa-ellipsis-v"></i>
                        </button>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="#" onclick="editCategory(${category.id})">
                                <i class="fas fa-edit me-2"></i>Edit Category
                            </a></li>
                            <li><a class="dropdown-item" href="#" onclick="addSubcategory(${category.id})">
                                <i class="fas fa-plus me-2"></i>Add Subcategory
                            </a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item text-danger" href="#" onclick="deleteCategory(${category.id})">
                                <i class="fas fa-trash me-2"></i>Delete Category
                            </a></li>
                        </ul>
                    </div>
                </div>
                <div class="card-body">
                    ${category.description ? `<p class="text-muted small">${category.description}</p>` : ''}
                    <div class="mb-3">
                        <small class="text-muted">Items: 0</small>
                    </div>

                    <h6 class="mb-2">Subcategories:</h6>
                    <div class="subcategories-list">
                        ${subcategoriesHtml}
                    </div>

                    <div class="mt-3">
                        <button class="btn btn-sm btn-outline-primary w-100" onclick="addSubcategory(${category.id})">
                            <i class="fas fa-plus me-2"></i>Add Subcategory
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Handle category form submission
 */
async function handleCategorySubmit(event) {
    event.preventDefault();

    const formData = {
        name: document.getElementById('categoryName').value.trim(),
        description: document.getElementById('categoryDescription').value.trim(),
        icon: document.getElementById('categoryIcon').value,
        color: document.getElementById('categoryColor').value
    };

    if (!formData.name) {
        showAlert('Category name is required', 'danger');
        return;
    }

    try {
        const categoryId = document.getElementById('categoryId').value;
        const url = categoryId ? `/api/categories/${categoryId}` : '/api/categories';
        const method = categoryId ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            const errorMessage = errorData.error || 'Failed to save category';
            console.error('Category save error:', errorMessage);
            showAlert(errorMessage, 'danger');
            return;
        }

        const result = await response.json();
        
        if (result.success) {
            // Close modal and reload categories
            const modal = bootstrap.Modal.getInstance(document.getElementById('categoryModal'));
            modal.hide();

            document.getElementById('categoryForm').reset();
            document.getElementById('categoryId').value = '';

            showAlert(categoryId ? 'Category updated successfully' : 'Category created successfully', 'success');
            loadCategories();
        } else {
            showAlert(result.error || 'Failed to save category', 'danger');
        }

    } catch (error) {
        console.error('Error saving category:', error);
        showAlert('Network error: ' + error.message, 'danger');
    }
}

/**
 * Handle subcategory form submission
 */
async function handleSubcategorySubmit(event) {
    event.preventDefault();

    const formData = {
        name: document.getElementById('subcategoryName').value.trim(),
        description: document.getElementById('subcategoryDescription').value.trim()
    };

    if (!formData.name) {
        showAlert('Subcategory name is required', 'danger');
        return;
    }

    try {
        const subcategoryId = document.getElementById('subcategoryId').value;
        const categoryId = document.getElementById('parentCategoryId').value;

        let url, method;
        if (subcategoryId) {
            url = `/api/subcategories/${subcategoryId}`;
            method = 'PUT';
        } else {
            url = `/api/categories/${categoryId}/subcategories`;
            method = 'POST';
        }

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to save subcategory');
        }

        // Close modal and reload categories
        const modal = bootstrap.Modal.getInstance(document.getElementById('subcategoryModal'));
        modal.hide();

        document.getElementById('subcategoryForm').reset();
        document.getElementById('subcategoryId').value = '';
        document.getElementById('parentCategoryId').value = '';

        showAlert(subcategoryId ? 'Subcategory updated successfully' : 'Subcategory created successfully', 'success');
        loadCategories();

    } catch (error) {
        console.error('Error saving subcategory:', error);
        showAlert(error.message, 'danger');
    }
}

/**
 * Edit a category
 */
function editCategory(categoryId) {
    const category = categories.find(c => c.id === categoryId);
    if (!category) return;

    document.getElementById('categoryId').value = category.id;
    document.getElementById('categoryName').value = category.name;
    document.getElementById('categoryDescription').value = category.description || '';
    document.getElementById('categoryIcon').value = category.icon || 'fas fa-box';
    document.getElementById('categoryColor').value = category.color || '#007bff';

    document.getElementById('categoryModalLabel').textContent = 'Edit Category';

    const modal = new bootstrap.Modal(document.getElementById('categoryModal'));
    modal.show();
}

/**
 * Add a subcategory to a category
 */
function addSubcategory(categoryId) {
    // Set the parent category ID
    document.getElementById('parentCategoryId').value = categoryId;

    // Clear the form
    document.getElementById('subcategoryForm').reset();
    document.getElementById('subcategoryId').value = '';

    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('subcategoryModal'));
    modal.show();
}

// Handle subcategory form submission
document.getElementById('subcategoryForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const subcategoryId = document.getElementById('subcategoryId').value;
    const parentCategoryId = document.getElementById('parentCategoryId').value;
    const formData = {
        name: document.getElementById('subcategoryName').value,
        description: document.getElementById('subcategoryDescription').value
    };

    try {
        let response;

        if (subcategoryId) {
            // Update existing subcategory
            response = await fetch(`/api/subcategories/${subcategoryId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin',
                body: JSON.stringify(formData)
            });
        } else {
            // Create new subcategory
            response = await fetch(`/api/categories/${parentCategoryId}/subcategories`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin',
                body: JSON.stringify(formData)
            });
        }

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to save subcategory');
        }

        const result = await response.json();

        if (result.success) {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('subcategoryModal'));
            modal.hide();

            // Show success message
            showAlert(subcategoryId ? 'Subcategory updated successfully!' : 'Subcategory created successfully!', 'success');

            // Reload categories
            loadCategories();
        } else {
            showAlert(result.error || 'Failed to save subcategory', 'danger');
        }
    } catch (error) {
        console.error('Error saving subcategory:', error);
        showAlert(error.message, 'danger');
    }
});

/**
 * Edit a subcategory
 */
async function editSubcategory(subcategoryId) {
    try {
        // Find the subcategory in the loaded categories data
        let subcategory = null;
        for (const category of categories) {
            if (category.subcategories) {
                subcategory = category.subcategories.find(sub => sub.id === subcategoryId);
                if (subcategory) break;
            }
        }

        if (!subcategory) {
            throw new Error('Subcategory not found');
        }

        document.getElementById('subcategoryId').value = subcategory.id;
        document.getElementById('parentCategoryId').value = subcategory.parent_id;
        document.getElementById('subcategoryName').value = subcategory.name;
        document.getElementById('subcategoryDescription').value = subcategory.description || '';

        document.getElementById('subcategoryModalLabel').textContent = 'Edit Subcategory';

        const modal = new bootstrap.Modal(document.getElementById('subcategoryModal'));
        modal.show();

    } catch (error) {
        console.error('Error loading subcategory:', error);
        showAlert('Failed to load subcategory', 'danger');
    }
}

/**
 * Delete a category
 */
async function deleteCategory(categoryId) {
    const category = categories.find(c => c.id === categoryId);
    if (!category) return;

    // Check if category has subcategories
    const hasSubcategories = category.subcategories && category.subcategories.length > 0;
    
    let confirmMessage = `Are you sure you want to delete the category "${category.name}"?`;
    if (hasSubcategories) {
        confirmMessage += `\n\nThis category has ${category.subcategories.length} subcategories. All subcategories will also be deleted.`;
    }
    confirmMessage += '\n\nThis action cannot be undone.';

    if (!confirm(confirmMessage)) {
        return;
    }

    try {
        const response = await fetch(`/api/categories/${categoryId}`, {
            method: 'DELETE',
            credentials: 'same-origin'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to delete category');
        }

        const result = await response.json();
        showAlert(result.message || 'Category deleted successfully', 'success');
        loadCategories();

    } catch (error) {
        console.error('Error deleting category:', error);
        showAlert(error.message, 'danger');
    }
}

/**
 * Delete a subcategory
 */
async function deleteSubcategory(subcategoryId) {
    // Find the subcategory name for confirmation
    let subcategoryName = 'this subcategory';
    for (const category of categories) {
        if (category.subcategories) {
            const sub = category.subcategories.find(s => s.id === subcategoryId);
            if (sub) {
                subcategoryName = sub.name;
                break;
            }
        }
    }

    if (!confirm(`Are you sure you want to delete "${subcategoryName}"? This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/subcategories/${subcategoryId}`, {
            method: 'DELETE',
            credentials: 'same-origin'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to delete subcategory');
        }

        const result = await response.json();
        showAlert(result.message || `Subcategory "${subcategoryName}" deleted successfully`, 'success');
        loadCategories();

    } catch (error) {
        console.error('Error deleting subcategory:', error);
        showAlert(error.message, 'danger');
    }
}

/**
 * Show loading spinner
 */
function showLoading(show) {
    const spinner = document.getElementById('loading-spinner');
    const container = document.getElementById('categories-container');

    if (show) {
        spinner.classList.remove('d-none');
        container.classList.add('d-none');
    } else {
        spinner.classList.add('d-none');
        container.classList.remove('d-none');
    }
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
    // Remove existing alerts
    const existingAlerts = document.querySelectorAll('.alert-dismissible');
    existingAlerts.forEach(alert => alert.remove());

    // Create new alert
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show mt-3`;
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
        <i class="fas fa-${type === 'danger' ? 'exclamation-triangle' : type === 'success' ? 'check-circle' : 'info-circle'}"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    // Insert at the top of the page or in the modal if it's open
    const modal = document.querySelector('.modal.show');
    if (modal) {
        const modalBody = modal.querySelector('.modal-body');
        modalBody.insertBefore(alertDiv, modalBody.firstChild);
    } else {
        const container = document.querySelector('.container-fluid');
        container.insertBefore(alertDiv, container.firstChild);
    }

    // Auto-remove after 8 seconds for errors, 5 seconds for others
    const timeout = type === 'danger' ? 8000 : 5000;
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, timeout);
}

// Reset modal forms when hidden
document.getElementById('categoryModal').addEventListener('hidden.bs.modal', function() {
    document.getElementById('categoryForm').reset();
    document.getElementById('categoryId').value = '';
    document.getElementById('categoryModalLabel').textContent = 'Add New Category';
});

document.getElementById('subcategoryModal').addEventListener('hidden.bs.modal', function() {
    document.getElementById('subcategoryForm').reset();
    document.getElementById('subcategoryId').value = '';
    document.getElementById('parentCategoryId').value = '';
    document.getElementById('subcategoryModalLabel').textContent = 'Add Subcategory';
});

// DOM Elements
const categoryForm = document.getElementById('categoryForm');
const categoryNameInput = document.getElementById('categoryName');
const categoryDescInput = document.getElementById('categoryDescription');
const parentCategorySelect = document.getElementById('parentCategory');
const saveCategoryBtn = document.getElementById('saveCategoryBtn');
const categoriesContainer = document.getElementById('categoriesContainer');

categoryForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const name = categoryNameInput.value.trim();
        const description = categoryDescInput.value.trim();
        const parentId = parentCategorySelect.value || null;

        if (!name) {
            showAlert('Category name is required', 'danger');
            return;
        }

        const categoryData = {
            name: name,
            description: description,
            parent_id: parentId
        };

        saveCategoryBtn.disabled = true;
        saveCategoryBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

        fetch('/api/categories', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(categoryData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showAlert(data.error, 'danger');
            } else {
                showAlert(data.message, 'success');
                categoryForm.reset();
                loadCategories();
                loadParentCategories();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Failed to save category', 'danger');
        })
        .finally(() => {
            saveCategoryBtn.disabled = false;
            saveCategoryBtn.innerHTML = '<i class="fas fa-save"></i> Save Category';
        });
    });

    function loadParentCategories() {
        fetch('/api/categories')
            .then(response => response.json())
            .then(data => {
                populateParentCategorySelect(data);
            })
            .catch(error => {
                console.error('Error loading parent categories:', error);
            });
    }

    function populateParentCategorySelect(categories) {
        if (!parentCategorySelect) return;

        // Clear existing options except the first one
        parentCategorySelect.innerHTML = '<option value="">None (Main Category)</option>';

        // Add only parent categories (those without parent_id)
        categories.forEach(category => {
            if (!category.parent_id) {
                const option = document.createElement('option');
                option.value = category.id;
                option.textContent = category.name;
                parentCategorySelect.appendChild(option);
            }
        });
    }