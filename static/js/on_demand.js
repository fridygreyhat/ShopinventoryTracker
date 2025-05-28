document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const productsTableBody = document.getElementById('productsTableBody');
    const categoryFilter = document.getElementById('categoryFilter');
    const searchInput = document.getElementById('searchInput');
    const statusFilter = document.getElementById('statusFilter');
    const applyFiltersBtn = document.getElementById('applyFiltersBtn');

    // Add Product Form Elements
    const addProductForm = document.getElementById('addProductForm');
    const saveProductBtn = document.getElementById('saveProductBtn');
    const categoryOptions = document.getElementById('categoryOptions');
    const editCategoryOptions = document.getElementById('editCategoryOptions');

    // Edit Product Form Elements
    const editProductForm = document.getElementById('editProductForm');
    const editProductId = document.getElementById('editProductId');
    const editProductName = document.getElementById('editProductName');
    const editProductCategory = document.getElementById('editProductCategory');
    const editProductDescription = document.getElementById('editProductDescription');
    const editProductBasePrice = document.getElementById('editProductBasePrice');
    const editProductionTime = document.getElementById('editProductionTime');
    const editProductMaterials = document.getElementById('editProductMaterials');
    const editProductActive = document.getElementById('editProductActive');
    const updateProductBtn = document.getElementById('updateProductBtn');
    const deleteProductBtn = document.getElementById('deleteProductBtn');
    
    // View Product Modal Elements
    const viewProductName = document.getElementById('viewProductName');
    const viewProductCategory = document.getElementById('viewProductCategory');
    const viewProductStatus = document.getElementById('viewProductStatus');
    const viewProductPrice = document.getElementById('viewProductPrice');
    const viewProductTime = document.getElementById('viewProductTime');
    const viewProductDescription = document.getElementById('viewProductDescription');
    const viewProductMaterials = document.getElementById('viewProductMaterials');
    const editProductBtn = document.getElementById('editProductBtn');
    
    // Delete Confirmation Modal Elements
    const deleteProductName = document.getElementById('deleteProductName');
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    
    // Bootstrap Modals
    const addProductModal = new bootstrap.Modal(document.getElementById('addProductModal'));
    const editProductModal = new bootstrap.Modal(document.getElementById('editProductModal'));
    const viewProductModal = new bootstrap.Modal(document.getElementById('viewProductModal'));
    const deleteConfirmModal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
    
    // Variables
    let currentProducts = [];
    let productToDelete = null;
    
    // Initialize
    loadCategories();
    loadProducts();
    
    // Event Listeners
    applyFiltersBtn.addEventListener('click', loadProducts);
    
    saveProductBtn.addEventListener('click', saveProduct);
    
    updateProductBtn.addEventListener('click', updateProduct);
    
    deleteProductBtn.addEventListener('click', function() {
        const productId = editProductId.value;
        const product = currentProducts.find(p => p.id == productId);
        if (product) {
            productToDelete = product;
            deleteProductName.textContent = product.name;
            editProductModal.hide();
            setTimeout(() => {
                deleteConfirmModal.show();
            }, 500);
        }
    });
    
    confirmDeleteBtn.addEventListener('click', function() {
        if (productToDelete) {
            deleteProduct(productToDelete.id);
        }
    });
    
    editProductBtn.addEventListener('click', function() {
        viewProductModal.hide();
        setTimeout(() => {
            editProductModal.show();
        }, 500);
    });
    
    // Search on enter key
    searchInput.addEventListener('keyup', function(event) {
        if (event.key === 'Enter') {
            loadProducts();
        }
    });
    
    // Functions
    function loadProducts() {
        // Get filter values
        const category = categoryFilter.value;
        const search = searchInput.value;
        const status = statusFilter.value;
        
        // Build query string
        let queryParams = [];
        if (category) {
            queryParams.push(`category=${encodeURIComponent(category)}`);
        }
        if (search) {
            queryParams.push(`search=${encodeURIComponent(search)}`);
        }
        if (status === 'active') {
            queryParams.push('active_only=true');
        } else if (status === 'inactive') {
            queryParams.push('active_only=false');
        }
        
        const queryString = queryParams.length > 0 ? `?${queryParams.join('&')}` : '';
        
        // Make API request
        fetch(`/api/on-demand${queryString}`)
            .then(response => response.json())
            .then(products => {
                currentProducts = products;
                displayProducts(products);
            })
            .catch(error => {
                console.error('Error loading products:', error);
                productsTableBody.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center text-danger">
                            <i class="fas fa-exclamation-circle me-2"></i> Error loading products
                        </td>
                    </tr>
                `;
            });
    }
    
    function loadCategories() {
        // Predefined categories list - same as inventory for consistency
        const predefinedCategories = [
            'Electronics', 
            'Accessories', 
            'Phones', 
            'Vehicle Spare Parts', 
            'Grocery', 
            'Others'
        ];
        
        fetch('/api/on-demand/categories')
            .then(response => response.json())
            .then(categories => {
                // Combine predefined categories with database categories
                // and remove duplicates
                let allCategories = [...predefinedCategories];
                
                // Add any categories from database that aren't in predefined list
                categories.forEach(category => {
                    if (!allCategories.includes(category)) {
                        allCategories.push(category);
                    }
                });
                
                // Sort alphabetically
                allCategories.sort();
                
                // Populate category filter
                categoryFilter.innerHTML = '<option value="">All Categories</option>';
                
                // Clear existing options
                categoryOptions.innerHTML = '';
                editCategoryOptions.innerHTML = '';
                
                // Add new options
                allCategories.forEach(category => {
                    // Add to filter dropdown
                    const option = document.createElement('option');
                    option.value = category;
                    option.textContent = category;
                    categoryFilter.appendChild(option);
                    
                    // Add to datalist for new product form
                    const dataOption1 = document.createElement('option');
                    dataOption1.value = category;
                    categoryOptions.appendChild(dataOption1);
                    
                    // Add to datalist for edit product form
                    const dataOption2 = document.createElement('option');
                    dataOption2.value = category;
                    editCategoryOptions.appendChild(dataOption2);
                });
            })
            .catch(error => {
                console.error('Error loading categories:', error);
                
                // Even if fetch fails, still load predefined categories
                // Sort alphabetically
                const sortedCategories = [...predefinedCategories].sort();
                
                // Clear existing options
                categoryFilter.innerHTML = '<option value="">All Categories</option>';
                categoryOptions.innerHTML = '';
                editCategoryOptions.innerHTML = '';
                
                // Add predefined categories
                sortedCategories.forEach(category => {
                    // Add to filter dropdown
                    const option = document.createElement('option');
                    option.value = category;
                    option.textContent = category;
                    categoryFilter.appendChild(option);
                    
                    // Add to datalist for new product form
                    const dataOption1 = document.createElement('option');
                    dataOption1.value = category;
                    categoryOptions.appendChild(dataOption1);
                    
                    // Add to datalist for edit product form
                    const dataOption2 = document.createElement('option');
                    dataOption2.value = category;
                    editCategoryOptions.appendChild(dataOption2);
                });
            });
    }
    
    function displayProducts(products) {
        if (products.length === 0) {
            productsTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center">No products found</td>
                </tr>
            `;
            return;
        }
        
        let html = '';
        
        products.forEach(product => {
            const statusBadge = product.is_active 
                ? '<span class="badge bg-success">Active</span>' 
                : '<span class="badge bg-secondary">Inactive</span>';
            
            html += `
                <tr data-id="${product.id}">
                    <td>
                        <a href="#" class="text-decoration-none view-product" data-id="${product.id}">
                            ${product.name}
                        </a>
                    </td>
                    <td>${product.category || 'Uncategorized'}</td>
                    <td><span class="currency-symbol">TZS</span> ${product.base_price.toLocaleString()}</td>
                    <td>${product.production_time || 0} hours</td>
                    <td>${statusBadge}</td>
                    <td>
                        <button class="btn btn-sm btn-info view-product" data-id="${product.id}">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-primary edit-product" data-id="${product.id}">
                            <i class="fas fa-edit"></i>
                        </button>
                    </td>
                </tr>
            `;
        });
        
        productsTableBody.innerHTML = html;
        
        // Add event listeners to action buttons
        document.querySelectorAll('.view-product').forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const productId = this.getAttribute('data-id');
                viewProduct(productId);
            });
        });
        
        document.querySelectorAll('.edit-product').forEach(button => {
            button.addEventListener('click', function() {
                const productId = this.getAttribute('data-id');
                loadProductForEdit(productId);
            });
        });
    }
    
    function saveProduct() {
        // Get form data
        const formData = new FormData(addProductForm);
        const productData = {};
        
        // Convert FormData to object
        for (const [key, value] of formData.entries()) {
            if (key === 'is_active') {
                productData[key] = true;  // Checkbox is only in FormData if checked
            } else {
                productData[key] = value;
            }
        }
        
        // Add missing checkbox if unchecked
        if (!formData.has('is_active')) {
            productData.is_active = false;
        }
        
        // Send to API
        fetch('/api/on-demand', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(productData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Show success message
            alert('Product added successfully!');
            
            // Reset form
            addProductForm.reset();
            
            // Hide modal
            addProductModal.hide();
            
            // Reload products
            loadProducts();
            loadCategories();
        })
        .catch(error => {
            console.error('Error adding product:', error);
            alert('Failed to add product. Please try again.');
        });
    }
    
    function loadProductForEdit(productId) {
        const product = currentProducts.find(p => p.id == productId);
        
        if (!product) {
            console.error('Product not found:', productId);
            return;
        }
        
        // Populate form
        editProductId.value = product.id;
        editProductName.value = product.name;
        editProductCategory.value = product.category || '';
        editProductDescription.value = product.description || '';
        editProductBasePrice.value = product.base_price;
        editProductionTime.value = product.production_time || 0;
        editProductMaterials.value = product.materials || '';
        editProductActive.checked = product.is_active;
        
        // Show modal
        editProductModal.show();
    }
    
    function updateProduct() {
        const productId = editProductId.value;
        
        // Get form data
        const formData = new FormData(editProductForm);
        const productData = {};
        
        // Convert FormData to object
        for (const [key, value] of formData.entries()) {
            if (key === 'is_active') {
                productData[key] = true;  // Checkbox is only in FormData if checked
            } else {
                productData[key] = value;
            }
        }
        
        // Add missing checkbox if unchecked
        if (!formData.has('is_active')) {
            productData.is_active = false;
        }
        
        // Send to API
        fetch(`/api/on-demand/${productId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(productData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Show success message
            alert('Product updated successfully!');
            
            // Hide modal
            editProductModal.hide();
            
            // Reload products
            loadProducts();
            loadCategories();
        })
        .catch(error => {
            console.error('Error updating product:', error);
            alert('Failed to update product. Please try again.');
        });
    }
    
    function deleteProduct(productId) {
        fetch(`/api/on-demand/${productId}`, {
            method: 'DELETE'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Show success message
            alert('Product deleted successfully!');
            
            // Hide modal
            deleteConfirmModal.hide();
            
            // Reset productToDelete
            productToDelete = null;
            
            // Reload products
            loadProducts();
            loadCategories();
        })
        .catch(error => {
            console.error('Error deleting product:', error);
            alert('Failed to delete product. Please try again.');
        });
    }
    
    function viewProduct(productId) {
        const product = currentProducts.find(p => p.id == productId);
        
        if (!product) {
            console.error('Product not found:', productId);
            return;
        }
        
        // Populate view modal
        viewProductName.textContent = product.name;
        viewProductCategory.textContent = product.category || 'Uncategorized';
        viewProductStatus.textContent = product.is_active ? 'Active' : 'Inactive';
        viewProductStatus.className = `badge ${product.is_active ? 'bg-success' : 'bg-secondary'} mb-2`;
        viewProductPrice.textContent = product.base_price.toLocaleString();
        viewProductTime.textContent = product.production_time || 0;
        
        // Handle description - show "No description available" if empty
        if (product.description && product.description.trim() !== '') {
            viewProductDescription.textContent = product.description;
        } else {
            viewProductDescription.innerHTML = '<em>No description available</em>';
        }
        
        // Handle materials - convert newlines to <br> tags
        if (product.materials && product.materials.trim() !== '') {
            viewProductMaterials.innerHTML = product.materials.replace(/\n/g, '<br>');
        } else {
            viewProductMaterials.innerHTML = '<em>No materials specified</em>';
        }
        
        // Set up edit button to load the same product
        editProductBtn.setAttribute('data-id', product.id);
        editProductBtn.onclick = function() {
            viewProductModal.hide();
            setTimeout(() => {
                loadProductForEdit(product.id);
            }, 500);
        };
        
        // Show modal
        viewProductModal.show();
    }
});