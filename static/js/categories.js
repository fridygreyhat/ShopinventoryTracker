
/**
 * Categories Management JavaScript
 * Handles CRUD operations for categories and subcategories
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize page
    loadCategories();
    
    // Event listeners
    document.getElementById('categoryForm').addEventListener('submit', handleCategorySubmit);
    document.getElementById('subcategoryForm').addEventListener('submit', handleSubcategorySubmit);
});

let categories = [];
let editingCategory = null;
let editingSubcategory = null;

/**
 * Load all categories from the server
 */
async function loadCategories() {
    try {
        showLoading(true);
        
        const response = await fetch('/api/categories');
        if (!response.ok) {
            throw new Error('Failed to load categories');
        }
        
        categories = await response.json();
        renderCategories();
        
    } catch (error) {
        console.error('Error loading categories:', error);
        showAlert('Failed to load categories', 'danger');
    } finally {
        showLoading(false);
    }
}

/**
 * Render categories in the UI
 */
function renderCategories() {
    const container = document.getElementById('categories-container');
    
    if (categories.length === 0) {
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
    
    container.innerHTML = categories.map(category => createCategoryCard(category)).join('');
}

/**
 * Create HTML for a category card
 */
function createCategoryCard(category) {
    const subcategoriesHtml = category.subcategories.length > 0 
        ? category.subcategories.map(sub => `
            <div class="subcategory-item d-flex justify-content-between align-items-center mb-1">
                <span class="text-muted small">
                    <i class="fas fa-chevron-right me-1"></i>${sub.name} (${sub.item_count} items)
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
            <div class="card h-100 category-card" style="border-left: 4px solid ${category.color}">
                <div class="card-header d-flex justify-content-between align-items-center" style="background-color: ${category.color}10">
                    <div class="d-flex align-items-center">
                        <i class="${category.icon} me-2" style="color: ${category.color}"></i>
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
                        <small class="text-muted">Items: ${category.item_count}</small>
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
            const error = await response.json();
            throw new Error(error.error || 'Failed to save category');
        }
        
        // Close modal and reload categories
        const modal = bootstrap.Modal.getInstance(document.getElementById('categoryModal'));
        modal.hide();
        
        document.getElementById('categoryForm').reset();
        document.getElementById('categoryId').value = '';
        
        showAlert(categoryId ? 'Category updated successfully' : 'Category created successfully', 'success');
        loadCategories();
        
    } catch (error) {
        console.error('Error saving category:', error);
        showAlert(error.message, 'danger');
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
    document.getElementById('parentCategoryId').value = categoryId;
    document.getElementById('subcategoryModalLabel').textContent = 'Add Subcategory';
    
    const modal = new bootstrap.Modal(document.getElementById('subcategoryModal'));
    modal.show();
}

/**
 * Edit a subcategory
 */
async function editSubcategory(subcategoryId) {
    try {
        const response = await fetch(`/api/subcategories/${subcategoryId}`);
        if (!response.ok) {
            throw new Error('Failed to load subcategory');
        }
        
        const subcategory = await response.json();
        
        document.getElementById('subcategoryId').value = subcategory.id;
        document.getElementById('parentCategoryId').value = subcategory.category_id;
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
    
    if (!confirm(`Are you sure you want to delete the category "${category.name}"? This action cannot be undone.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/categories/${categoryId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to delete category');
        }
        
        showAlert('Category deleted successfully', 'success');
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
    if (!confirm('Are you sure you want to delete this subcategory? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/subcategories/${subcategoryId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to delete subcategory');
        }
        
        showAlert('Subcategory deleted successfully', 'success');
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
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert at the top of the page
    const container = document.querySelector('.container-fluid');
    container.insertBefore(alertDiv, container.firstChild);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
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
