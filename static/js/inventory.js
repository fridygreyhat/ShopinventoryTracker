document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const searchInput = document.getElementById('searchInput');
    const importButton = document.getElementById('importButton');
    const importResult = document.getElementById('importResult');

    // Bulk Import Handler
    importButton.addEventListener('click', function() {
        const fileInput = document.getElementById('csvFile');
        const file = fileInput.files[0];

        if (!file) {
            showImportError('Please select a file');
            return;
        }

        if (!file.name.endsWith('.csv')) {
            showImportError('Please select a CSV file');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        importButton.disabled = true;
        importResult.className = 'alert alert-info';
        importResult.textContent = 'Importing...';
        importResult.classList.remove('d-none');

        fetch('/api/inventory/bulk-import', {
            method: 'POST',
            body: formData,
            headers: {
                'Accept': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                importResult.className = 'alert alert-success';
                importResult.textContent = `Successfully imported ${data.imported_count} items`;
                if (data.errors.length > 0) {
                    const errorList = document.createElement('ul');
                    data.errors.forEach(error => {
                        const li = document.createElement('li');
                        li.textContent = error;
                        errorList.appendChild(li);
                    });
                    importResult.appendChild(errorList);
                }

                // Reset file input and reload inventory
                fileInput.value = '';
                loadInventory();
                loadCategories();
            } else {
                showImportError(data.error);
            }
        })
        .catch(error => {
            showImportError('Import failed: ' + error.message);
        })
        .finally(() => {
            importButton.disabled = false;
        });
    });

    function showImportError(message) {
        importResult.className = 'alert alert-danger';
        importResult.textContent = message;
        importResult.classList.remove('d-none');
    }
    const categoryFilter = document.getElementById('categoryFilter');
    const minStockFilter = document.getElementById('minStockFilter');
    const maxStockFilter = document.getElementById('maxStockFilter');
    const resetFiltersBtn = document.getElementById('resetFilters');
    const inventoryTable = document.getElementById('inventoryTable');
    const noItemsMessage = document.getElementById('noItemsMessage');

    // Add Item Form Elements
    const addItemForm = document.getElementById('addItemForm');
    const saveItemBtn = document.getElementById('saveItemBtn');

    // Edit Item Form Elements
    const editItemForm = document.getElementById('editItemForm');
    const updateItemBtn = document.getElementById('updateItemBtn');

    // Delete Confirmation Elements
    const deleteConfirmModal = document.getElementById('deleteConfirmModal');
    const deleteItemName = document.getElementById('deleteItemName');
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');

    // Initialize
    loadInventory();
    loadCategories();

    // Unit type change handler
    document.getElementById('itemUnitType').addEventListener('change', function() {
        const quantityInput = document.getElementById('itemQuantity');
        if (this.value === 'weight') {
            quantityInput.setAttribute('step', '0.1');
            quantityInput.setAttribute('min', '0.1');
            quantityInput.placeholder = 'Enter weight in kg';
        } else {
            quantityInput.setAttribute('step', '1');
            quantityInput.setAttribute('min', '1');
            quantityInput.placeholder = 'Enter quantity';
        }
    });

    // Event Listeners
    searchInput.addEventListener('input', applyFilters);
    categoryFilter.addEventListener('change', applyFilters);
    minStockFilter.addEventListener('input', applyFilters);
    maxStockFilter.addEventListener('input', applyFilters);
    resetFiltersBtn.addEventListener('click', resetFilters);

    // Add Item Event Listener
    saveItemBtn.addEventListener('click', saveNewItem);

    // Update Item Event Listener
    updateItemBtn.addEventListener('click', updateItem);

    // Functions
    function loadInventory() {
        fetch('/api/inventory')
            .then(response => response.json())
            .then(data => {
                if (data && data.length > 0) {
                    displayInventory(data);
                    noItemsMessage.classList.add('d-none');
                } else {
                    inventoryTable.innerHTML = '<tr><td colspan="7" class="text-center">No inventory items found</td></tr>';
                    noItemsMessage.classList.remove('d-none');
                }
            })
            .catch(error => {
                console.error('Error loading inventory:', error);
                inventoryTable.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Error loading inventory. Please try again.</td></tr>';
            });
    }

    function loadCategories() {
        // Predefined categories list as fallback
        const predefinedCategories = [
            'Electronics', 
            'Accessories', 
            'Phones', 
            'Vehicle Spare Parts', 
            'Grocery', 
            'Others'
        ];

        // First try to load from the new Categories API
        fetch('/api/categories')
            .then(response => response.json())
            .then(categoriesData => {
                let allCategories = [];

                // Extract category names from the Categories API
                if (categoriesData && categoriesData.length > 0) {
                    allCategories = categoriesData.map(cat => cat.name);
                }

                // If no categories from API, use predefined ones
                if (allCategories.length === 0) {
                    allCategories = [...predefinedCategories];
                }

                // Also fetch legacy inventory categories and merge them
                return fetch('/api/inventory/categories')
                    .then(response => response.json())
                    .then(legacyCategories => {
                        // Add any legacy categories that aren't already included
                        legacyCategories.forEach(category => {
                            if (!allCategories.includes(category)) {
                                allCategories.push(category);
                            }
                        });

                        // Sort alphabetically
                        allCategories.sort();

                        // Update categories in filter dropdown
                        categoryFilter.innerHTML = '<option value="">All Categories</option>';

                        // Also update categories in the add/edit forms
                        const itemCategorySelect = document.getElementById('itemCategory');
                        const editItemCategorySelect = document.getElementById('editItemCategory');

                        itemCategorySelect.innerHTML = '<option value="">Select a category</option>';
                        editItemCategorySelect.innerHTML = '<option value="">Select a category</option>';

                        allCategories.forEach(category => {
                            // Add to filter dropdown
                            const option = document.createElement('option');
                            option.value = category;
                            option.textContent = category;
                            categoryFilter.appendChild(option);

                            // Add to new item form
                            const newItemOption = document.createElement('option');
                            newItemOption.value = category;
                            newItemOption.textContent = category;
                            itemCategorySelect.appendChild(newItemOption);

                            // Add to edit item form
                            const editItemOption = document.createElement('option');
                            editItemOption.value = category;
                            editItemOption.textContent = category;
                            editItemCategorySelect.appendChild(editItemOption);
                        });

                        // Also add subcategories from the Categories API
                        if (categoriesData && categoriesData.length > 0) {
                            categoriesData.forEach(category => {
                                if (category.subcategories && category.subcategories.length > 0) {
                                    category.subcategories.forEach(subcategory => {
                                        // Add subcategory to filter dropdown
                                        const subOption = document.createElement('option');
                                        subOption.value = subcategory.name;
                                        subOption.textContent = `${category.name} > ${subcategory.name}`;
                                        categoryFilter.appendChild(subOption);

                                        // Add subcategory to new item form
                                        const newSubOption = document.createElement('option');
                                        newSubOption.value = subcategory.name;
                                        newSubOption.textContent = `${category.name} > ${subcategory.name}`;
                                        itemCategorySelect.appendChild(newSubOption);

                                        // Add subcategory to edit item form
                                        const editSubOption = document.createElement('option');
                                        editSubOption.value = subcategory.name;
                                        editSubOption.textContent = `${category.name} > ${subcategory.name}`;
                                        editItemCategorySelect.appendChild(editSubOption);
                                    });
                                }
                            });
                        }
                    });
            })
            .catch(error => {
                console.error('Error loading categories:', error);

                // Fallback to predefined categories
                const itemCategorySelect = document.getElementById('itemCategory');
                const editItemCategorySelect = document.getElementById('editItemCategory');

                // Sort alphabetically
                const sortedCategories = [...predefinedCategories].sort();

                // Clear and populate dropdowns with predefined categories
                categoryFilter.innerHTML = '<option value="">All Categories</option>';
                itemCategorySelect.innerHTML = '<option value="">Select a category</option>';
                editItemCategorySelect.innerHTML = '<option value="">Select a category</option>';

                sortedCategories.forEach(category => {
                    // Add to filter dropdown
                    const option = document.createElement('option');
                    option.value = category;
                    option.textContent = category;
                    categoryFilter.appendChild(option);

                    // Add to new item form
                    const newItemOption = document.createElement('option');
                    newItemOption.value = category;
                    newItemOption.textContent = category;
                    itemCategorySelect.appendChild(newItemOption);

                    // Add to edit item form
                    const editItemOption = document.createElement('option');
                    editItemOption.value = category;
                    editItemOption.textContent = category;
                    editItemCategorySelect.appendChild(editItemOption);
                });
            });
    }

    // Calculate inventory health based on quantity
    function calculateInventoryHealth(quantity) {
        if (quantity <= 0) {
            return {
                status: 'critical',
                label: 'Out of Stock',
                color: 'danger',
                icon: 'exclamation-circle',
                percentage: 0
            };
        } else if (quantity <= 5) {
            return {
                status: 'low',
                label: 'Low Stock',
                color: 'warning',
                icon: 'exclamation-triangle',
                percentage: 25
            };
        } else if (quantity <= 10) {
            return {
                status: 'medium',
                label: 'Medium Stock',
                color: 'info',
                icon: 'info-circle',
                percentage: 50
            };
        } else if (quantity <= 20) {
            return {
                status: 'good',
                label: 'Good Stock',
                color: 'primary',
                icon: 'check-circle',
                percentage: 75
            };
        } else {
            return {
                status: 'optimal',
                label: 'Optimal Stock',
                color: 'success',
                icon: 'check-double',
                percentage: 100
            };
        }
    }

    // Generate health indicator HTML
    function generateHealthIndicator(quantity) {
        const health = calculateInventoryHealth(quantity);

        return `
            <div class="inventory-health">
                <div class="health-indicator">
                    <div class="progress" style="height: 8px;" title="${health.label}">
                        <div class="progress-bar bg-${health.color}" role="progressbar" 
                             style="width: ${health.percentage}%" 
                             aria-valuenow="${health.percentage}" aria-valuemin="0" aria-valuemax="100"></div>
                    </div>
                    <div class="mt-1 d-flex align-items-center">
                        <i class="fas fa-${health.icon} text-${health.color} me-1"></i>
                        <span class="small ${quantity <= 5 ? 'fw-bold' : ''}">${quantity} ${quantity <= 0 ? health.label : 'units'}</span>
                    </div>
                </div>
            </div>
        `;
    }

    function displayInventory(items) {
        inventoryTable.innerHTML = '';

        items.forEach(item => {
            const row = document.createElement('tr');

            // Determine stock status for row styling
            let stockStatusClass = '';
            if (item.quantity <= 0) {
                stockStatusClass = 'table-danger';
            } else if (item.quantity <= 5) {
                stockStatusClass = 'table-warning';
            }

            if (stockStatusClass) {
                row.classList.add(stockStatusClass);
            }

            row.innerHTML = `
                <td>${item.id}</td>
                <td>
                    <a href="/item/${item.id}" class="text-decoration-none">
                        ${item.name}
                    </a>
                </td>
                <td>${item.sku || ''}</td>
                <td>${item.category || 'Uncategorized'}</td>
                <td>
                    ${generateHealthIndicator(item.quantity)}
                </td>
                <td>
                    <small class="text-muted">Buying: </small><span class="currency-symbol">TZS</span> ${item.buying_price ? item.buying_price.toLocaleString() : 0}<br>
                    <small class="text-muted">Retail: </small><span class="currency-symbol">TZS</span> ${item.selling_price_retail ? item.selling_price_retail.toLocaleString() : 0}<br>
                    <small class="text-muted">Wholesale: </small><span class="currency-symbol">TZS</span> ${item.selling_price_wholesale ? item.selling_price_wholesale.toLocaleString() : 0}
                </td>
                <td>
                    <div class="btn-group" role="group">
                        <a href="/item/${item.id}" class="btn btn-sm btn-info">
                            <i class="fas fa-eye"></i>
                        </a>
                        <button type="button" class="btn btn-sm btn-primary edit-item-btn" data-item-id="${item.id}">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-danger delete-item-btn" data-item-id="${item.id}" data-item-name="${item.name}">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            `;

            inventoryTable.appendChild(row);
        });

        // Add event listeners to the edit and delete buttons
        document.querySelectorAll('.edit-item-btn').forEach(button => {
            button.addEventListener('click', function() {
                const itemId = this.dataset.itemId;
                loadItemForEdit(itemId);
            });
        });

        document.querySelectorAll('.delete-item-btn').forEach(button => {
            button.addEventListener('click', function() {
                const itemId = this.dataset.itemId;
                const itemName = this.dataset.itemName;

                // Set the item name in the confirmation modal
                deleteItemName.textContent = itemName;

                // Set the item ID to the confirm button
                confirmDeleteBtn.dataset.itemId = itemId;

                // Show the delete confirmation modal
                const modal = new bootstrap.Modal(deleteConfirmModal);
                modal.show();
            });
        });
    }

    function applyFilters() {
        const searchTerm = searchInput.value.trim();
        const category = categoryFilter.value;
        const minStock = minStockFilter.value ? parseInt(minStockFilter.value) : '';
        const maxStock = maxStockFilter.value ? parseInt(maxStockFilter.value) : '';

        let url = '/api/inventory?';

        if (searchTerm) {
            url += `search=${encodeURIComponent(searchTerm)}&`;
        }

        if (category) {
            url += `category=${encodeURIComponent(category)}&`;
        }

        if (minStock !== '') {
            url += `min_stock=${minStock}&`;
        }

        if (maxStock !== '') {
            url += `max_stock=${maxStock}&`;
        }

        // Remove trailing ampersand
        url = url.replace(/&$/, '');

        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data && data.length > 0) {
                    displayInventory(data);
                    noItemsMessage.classList.add('d-none');
                } else {
                    inventoryTable.innerHTML = '<tr><td colspan="7" class="text-center">No items match your search criteria</td></tr>';
                    noItemsMessage.classList.add('d-none');
                }
            })
            .catch(error => {
                console.error('Error applying filters:', error);
                inventoryTable.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Error applying filters. Please try again.</td></tr>';
            });
    }

    function resetFilters() {
        searchInput.value = '';
        categoryFilter.value = '';
        minStockFilter.value = '';
        maxStockFilter.value = '';

        loadInventory();
    }

    function saveNewItem() {
        // Get form values
        const name = document.getElementById('itemName').value.trim();
        const sku = document.getElementById('itemSKU').value.trim();
        const description = document.getElementById('itemDescription').value.trim();
        const category = document.getElementById('itemCategory').value.trim();
        const quantityStr = document.getElementById('itemQuantity').value.trim();

        // Get price fields
        const buyingPriceStr = document.getElementById('itemBuyingPrice').value.trim();
        const sellingPriceRetailStr = document.getElementById('itemSellingPriceRetail').value.trim();
        const sellingPriceWholesaleStr = document.getElementById('itemSellingPriceWholesale').value.trim();

        // Get sales type
        const salesType = document.querySelector('input[name="salesType"]:checked').value;

        // Validate required fields
        if (!name) {
            alert('Item name is required');
            return;
        }

        const quantity = parseInt(quantityStr);
        if (isNaN(quantity) || quantity < 0) {
            alert('Quantity must be a non-negative number');
            return;
        }

        // Validate price fields
        const buyingPrice = parseFloat(buyingPriceStr) || 0;
        if (buyingPrice < 0) {
            alert('Buying price must be a non-negative number');
            return;
        }

        const sellingPriceRetail = parseFloat(sellingPriceRetailStr) || 0;
        if (sellingPriceRetail < 0) {
            alert('Retail price must be a non-negative number');
            return;
        }

        const sellingPriceWholesale = parseFloat(sellingPriceWholesaleStr) || 0;
        if (sellingPriceWholesale < 0) {
            alert('Wholesale price must be a non-negative number');
            return;
        }

        // Create item object
        const newItem = {
            name,
            sku,
            description,
            category,
            quantity,
            buying_price: buyingPrice,
            selling_price_retail: sellingPriceRetail,
            selling_price_wholesale: sellingPriceWholesale,
            price: sellingPriceRetail, // For backward compatibility
            sales_type: salesType
        };

        // Send POST request to API
        fetch('/api/inventory', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(newItem)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to add item');
            }
            return response.json();
        })
        .then(data => {
            // Reset form
            addItemForm.reset();

            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('addItemModal'));
            modal.hide();

            // Reload inventory
            loadInventory();

            // Reload categories (in case a new category was added)
            loadCategories();

            // Refresh dashboard if function exists
            if (typeof window.refreshDashboard === 'function') {
                window.refreshDashboard();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to add item: ' + error.message);
        });
    }

    function loadItemForEdit(itemId) {
        fetch(`/api/inventory/${itemId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to load item details');
                }
                return response.json();
            })
            .then(item => {
                // Fill the edit form with item details
                document.getElementById('editItemId').value = item.id;
                document.getElementById('editItemName').value = item.name || '';
                document.getElementById('editItemSKU').value = item.sku || '';
                document.getElementById('editItemDescription').value = item.description || '';
                document.getElementById('editItemCategory').value = item.category || '';
                document.getElementById('editItemQuantity').value = item.quantity || 0;

                // Price fields
                document.getElementById('editItemBuyingPrice').value = item.buying_price || 0;
                document.getElementById('editItemSellingPriceRetail').value = item.selling_price_retail || 0;
                document.getElementById('editItemSellingPriceWholesale').value = item.selling_price_wholesale || 0;

                // Sales type
                const salesType = item.sales_type || 'both';
                document.getElementById(`editSalesType${salesType.charAt(0).toUpperCase() + salesType.slice(1)}`).checked = true;

                // Show the edit modal
                const editModal = new bootstrap.Modal(document.getElementById('editItemModal'));
                editModal.show();
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Failed to load item details: ' + error.message);
            });
    }

    function updateItem() {
        const itemId = document.getElementById('editItemId').value;

        // Get form values
        const name = document.getElementById('editItemName').value.trim();
        const sku = document.getElementById('editItemSKU').value.trim();
        const description = document.getElementById('editItemDescription').value.trim();
        const category = document.getElementById('editItemCategory').value.trim();
        const quantityStr = document.getElementById('editItemQuantity').value.trim();

        // Get price fields
        const buyingPriceStr = document.getElementById('editItemBuyingPrice').value.trim();
        const sellingPriceRetailStr = document.getElementById('editItemSellingPriceRetail').value.trim();
        const sellingPriceWholesaleStr = document.getElementById('editItemSellingPriceWholesale').value.trim();

        // Get sales type
        const salesType = document.querySelector('input[name="editSalesType"]:checked').value;

        // Validate required fields
        if (!name) {
            alert('Item name is required');
            return;
        }

        const quantity = parseInt(quantityStr);
        if (isNaN(quantity) || quantity < 0) {
            alert('Quantity must be a non-negative number');
            return;
        }

        // Validate price fields
        const buyingPrice = parseFloat(buyingPriceStr) || 0;
        if (buyingPrice < 0) {
            alert('Buying price must be a non-negative number');
            return;
        }

        const sellingPriceRetail = parseFloat(sellingPriceRetailStr) || 0;
        if (sellingPriceRetail < 0) {
            alert('Retail price must be a non-negative number');
            return;
        }

        const sellingPriceWholesale = parseFloat(sellingPriceWholesaleStr) || 0;
        if (sellingPriceWholesale < 0) {
            alert('Wholesale price must be a non-negative number');
            return;
        }

        // Create updated item object
        const updatedItem = {
            name,
            sku,
            description,
            category,
            quantity,
            buying_price: buyingPrice,
            selling_price_retail: sellingPriceRetail,
            selling_price_wholesale: sellingPriceWholesale,
            price: sellingPriceRetail, // For backward compatibility
            sales_type: salesType
        };

        // Send PUT request to API
        fetch(`/api/inventory/${itemId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updatedItem)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to update item');
            }
            return response.json();
        })
        .then(data => {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('editItemModal'));
            modal.hide();

            // Reload inventory
            loadInventory();

            // Reload categories (in case a new category was added)
            loadCategories();

            // Refresh dashboard if function exists
            if (typeof window.refreshDashboard === 'function') {
                window.refreshDashboard();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to update item: ' + error.message);
        });
    }

    // Set up delete confirmation
    confirmDeleteBtn.addEventListener('click', function() {
        const itemId = this.dataset.itemId;

        fetch(`/api/inventory/${itemId}`, {
            method: 'DELETE'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to delete item');
            }
            return response.json();
        })
        .then(data => {
            // Close the modal
            const modal = bootstrap.Modal.getInstance(deleteConfirmModal);
            modal.hide();

            // Reload inventory
            loadInventory();

            // Refresh dashboard if function exists
            if (typeof window.refreshDashboard === 'function') {
                window.refreshDashboard();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to delete item: ' + error.message);
        });
    });
});