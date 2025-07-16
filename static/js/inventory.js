document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const searchInput = document.getElementById('searchInput');
    const importButton = document.getElementById('importButton');
    const importResult = document.getElementById('importResult');

    // Format details handler
    const showFormatDetailsBtn = document.getElementById('showFormatDetails');
    const formatDetailsPanel = document.getElementById('formatDetailsPanel');
    const formatDetailsContent = document.getElementById('formatDetailsContent');

    if (showFormatDetailsBtn) {
        showFormatDetailsBtn.addEventListener('click', function() {
            if (formatDetailsPanel.classList.contains('d-none')) {
                // Show and load format details
                formatDetailsPanel.classList.remove('d-none');
                loadFormatDetails();
            } else {
                // Hide format details
                formatDetailsPanel.classList.add('d-none');
            }
        });
    }

    function loadFormatDetails() {
        fetch('/api/inventory/csv-template')
            .then(response => response.json())
            .then(data => {
                let detailsHTML = '<div class="row">';

                // Required fields
                detailsHTML += '<div class="col-md-6"><h6 class="text-success">Required Fields:</h6><ul>';
                data.required_fields.forEach(field => {
                    detailsHTML += `<li><code>${field}</code>: ${data.field_descriptions[field]}</li>`;
                });
                detailsHTML += '</ul></div>';

                // Optional fields
                detailsHTML += '<div class="col-md-6"><h6 class="text-info">Optional Fields:</h6><ul class="small">';
                data.optional_fields.forEach(field => {
                    detailsHTML += `<li><code>${field}</code>: ${data.field_descriptions[field]}</li>`;
                });
                detailsHTML += '</ul></div>';

                detailsHTML += '</div>';

                // Example
                detailsHTML += '<div class="mt-3"><h6>Example Row:</h6>';
                detailsHTML += `<code class="small">${data.example_row}</code></div>`;

                formatDetailsContent.innerHTML = detailsHTML;
            })
            .catch(error => {
                formatDetailsContent.innerHTML = '<div class="text-danger">Failed to load format details</div>';
            });
    }

    // Bulk Import Handler
    importButton.addEventListener('click', function() {
        const fileInput = document.getElementById('csvFile');
        const file = fileInput.files[0];

        if (!file) {
            showImportError('Please select a file');
            return;
        }

        if (!file.name.toLowerCase().endsWith('.csv')) {
            showImportError('Please select a CSV file');
            return;
        }

        // Check file size (limit to 5MB)
        if (file.size > 5 * 1024 * 1024) {
            showImportError('File size too large. Please select a file smaller than 5MB.');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        // Update button state
        importButton.disabled = true;
        const originalButtonText = importButton.innerHTML;
        importButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Importing...';

        importResult.className = 'alert alert-info';
        importResult.innerHTML = '<i class="fas fa-info-circle"></i> Processing your CSV file...';
        importResult.classList.remove('d-none');

        fetch('/api/inventory/bulk-import', {
            method: 'POST',
            body: formData,
            headers: {
                'Accept': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                importResult.className = 'alert alert-success';
                importResult.innerHTML = `
                    <div class="d-flex align-items-center">
                        <i class="fas fa-check-circle me-2"></i>
                        <div>
                            <strong>Success!</strong> Imported ${data.imported_count} out of ${data.total_rows} items
                        </div>
                    </div>
                `;

                if (data.errors && data.errors.length > 0) {
                    importResult.innerHTML += `
                        <hr class="my-2">
                        <div class="mt-2">
                            <strong><i class="fas fa-exclamation-triangle text-warning"></i> Warnings (${data.errors.length}):</strong>
                            <div class="mt-1" style="max-height: 200px; overflow-y: auto;">
                    `;

                    data.errors.forEach(error => {
                        importResult.innerHTML += `<div class="small text-muted">• ${error}</div>`;
                    });

                    importResult.innerHTML += '</div></div>';
                }

                // Reset file input and reload inventory
                fileInput.value = '';
                loadInventory();
                loadCategories();

                // Hide success message after 8 seconds
                setTimeout(() => {
                    importResult.classList.add('d-none');
                }, 8000);
            } else {
                showImportError(data.error || 'Import failed');
            }
        })
        .catch(error => {
            console.error('Import error:', error);
            showImportError('Import failed: ' + error.message);
        })
        .finally(() => {
            importButton.disabled = false;
            importButton.innerHTML = originalButtonText;
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
        fetch('/api/inventory?format=simple')
            .then(response => response.json())
            .then(data => {
                // Handle both simple format and enhanced format
                const items = Array.isArray(data) ? data : (data.items || []);
                
                if (items && items.length > 0) {
                    displayInventory(items);
                    noItemsMessage.classList.add('d-none');
                    
                    // Update inventory count if available
                    if (data.total_count !== undefined) {
                        updateInventoryCount(data.total_count);
                    }
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

    function updateInventoryCount(count) {
        const countElements = document.querySelectorAll('.inventory-count');
        countElements.forEach(element => {
            element.textContent = count.toLocaleString();
        });
    }

    function loadCategories() {
        fetch('/api/categories')
            .then(response => response.json())
            .then(data => {
                // Update category filter dropdown
                categoryFilter.innerHTML = '<option value="">All Categories</option>';

                // Add parent categories and their subcategories with proper hierarchy
                data.forEach(category => {
                    // Add main category
                    const option = document.createElement('option');
                    option.value = category.name;
                    option.textContent = `📁 ${category.name} (${category.total_item_count || 0} items)`;
                    categoryFilter.appendChild(option);

                    // Add subcategories if they exist
                    if (category.subcategories && category.subcategories.length > 0) {
                        category.subcategories.forEach(subcategory => {
                            const subOption = document.createElement('option');
                            subOption.value = subcategory.name;
                            subOption.textContent = `  📄 ${subcategory.name} (${subcategory.item_count || 0} items)`;
                            categoryFilter.appendChild(subOption);
                        });
                    }
                });

                // Store categories data globally for use in item forms
                window.categoriesData = data;
                
                // Update item form category dropdowns
                updateItemFormCategoryDropdowns(data);
            })
            .catch(error => {
                console.error('Error loading categories:', error);
                inventoryTable.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Error loading inventory. Please try again.</td></tr>';
            });
    }

    function updateItemFormCategoryDropdowns(categories) {
        // Update Add Item form category dropdown
        const addItemCategorySelect = document.getElementById('itemCategory');
        if (addItemCategorySelect) {
            addItemCategorySelect.innerHTML = '<option value="">Select a category</option>';
            
            if (categories && categories.length > 0) {
                categories.forEach(category => {
                    // Add main category
                    const option = document.createElement('option');
                    option.value = category.name;
                    option.setAttribute('data-category-id', category.id);
                    option.setAttribute('data-is-subcategory', 'false');
                    option.textContent = `📁 ${category.name}`;
                    addItemCategorySelect.appendChild(option);

                    // Add subcategories if they exist
                    if (category.subcategories && category.subcategories.length > 0) {
                        category.subcategories.forEach(subcategory => {
                            const subOption = document.createElement('option');
                            subOption.value = subcategory.name;
                            subOption.setAttribute('data-category-id', subcategory.id);
                            subOption.setAttribute('data-parent-id', category.id);
                            subOption.setAttribute('data-is-subcategory', 'true');
                            subOption.textContent = `  └─ ${subcategory.name}`;
                            addItemCategorySelect.appendChild(subOption);
                        });
                    }
                });
            } else {
                // Add option to create categories if none exist
                const createOption = document.createElement('option');
                createOption.value = '';
                createOption.textContent = 'No categories available - Create one first';
                createOption.disabled = true;
                addItemCategorySelect.appendChild(createOption);
            }
        }

        // Update Edit Item form category dropdown
        const editItemCategorySelect = document.getElementById('editItemCategory');
        if (editItemCategorySelect) {
            editItemCategorySelect.innerHTML = '<option value="">Select a category</option>';
            
            if (categories && categories.length > 0) {
                categories.forEach(category => {
                    // Add main category
                    const option = document.createElement('option');
                    option.value = category.name;
                    option.setAttribute('data-category-id', category.id);
                    option.setAttribute('data-is-subcategory', 'false');
                    option.textContent = `📁 ${category.name}`;
                    editItemCategorySelect.appendChild(option);

                    // Add subcategories if they exist
                    if (category.subcategories && category.subcategories.length > 0) {
                        category.subcategories.forEach(subcategory => {
                            const subOption = document.createElement('option');
                            subOption.value = subcategory.name;
                            subOption.setAttribute('data-category-id', subcategory.id);
                            subOption.setAttribute('data-parent-id', category.id);
                            subOption.setAttribute('data-is-subcategory', 'true');
                            subOption.textContent = `  └─ ${subcategory.name}`;
                            editItemCategorySelect.appendChild(subOption);
                        });
                    }
                });
            } else {
                // Add option to create categories if none exist
                const createOption = document.createElement('option');
                createOption.value = '';
                createOption.textContent = 'No categories available - Create one first';
                createOption.disabled = true;
                editItemCategorySelect.appendChild(createOption);
            }
        }
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

        let url = '/api/inventory?format=simple';

        if (searchTerm) {
            url += `&search=${encodeURIComponent(searchTerm)}`;
        }

        if (category) {
            url += `&category=${encodeURIComponent(category)}`;
        }

        if (minStock !== '') {
            url += `&min_stock=${minStock}`;
        }

        if (maxStock !== '') {
            url += `&max_stock=${maxStock}`;
        }

        fetch(url)
            .then(response => response.json())
            .then(data => {
                // Handle both simple format and enhanced format
                const items = Array.isArray(data) ? data : (data.items || []);
                
                if (items && items.length > 0) {
                    displayInventory(items);
                    noItemsMessage.classList.add('d-none');
                    
                    // Show filter results count
                    const resultsCount = Array.isArray(data) ? data.length : (data.total_count || items.length);
                    showFilterResults(resultsCount);
                } else {
                    inventoryTable.innerHTML = '<tr><td colspan="7" class="text-center">No items match your search criteria</td></tr>';
                    noItemsMessage.classList.add('d-none');
                    showFilterResults(0);
                }
            })
            .catch(error => {
                console.error('Error applying filters:', error);
                inventoryTable.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Error applying filters. Please try again.</td></tr>';
            });
    }

    function showFilterResults(count) {
        // Update any results counter elements
        const resultsElements = document.querySelectorAll('.filter-results-count');
        resultsElements.forEach(element => {
            element.textContent = `${count} item${count !== 1 ? 's' : ''} found`;
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
        const category = document.getElementById('itemCategory').value.trim() || 'Uncategorized';
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

        // Get category information
        const categorySelect = document.getElementById('itemCategory');
        const selectedOption = categorySelect.options[categorySelect.selectedIndex];
        const categoryId = selectedOption ? selectedOption.getAttribute('data-category-id') : null;
        const isSubcategory = selectedOption ? selectedOption.getAttribute('data-is-subcategory') === 'true' : false;

        // Create item object
        const newItem = {
            name,
            sku,
            description,
            category,
            category_id: categoryId ? parseInt(categoryId) : null,
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
        const category = document.getElementById('editItemCategory').value.trim() || 'Uncategorized';
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

        // Get category information
        const categorySelect = document.getElementById('editItemCategory');
        const selectedOption = categorySelect.options[categorySelect.selectedIndex];
        const categoryId = selectedOption ? selectedOption.getAttribute('data-category-id') : null;
        const isSubcategory = selectedOption ? selectedOption.getAttribute('data-is-subcategory') === 'true' : false;

        // Create updated item object
        const updatedItem = {
            name,
            sku,
            description,
            category,
            category_id: categoryId ? parseInt(categoryId) : null,
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