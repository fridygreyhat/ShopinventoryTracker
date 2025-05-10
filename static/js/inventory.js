document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const searchInput = document.getElementById('searchInput');
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
    
    // Load initial data
    loadInventory();
    loadCategories();
    
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
        // Predefined categories list
        const predefinedCategories = [
            'Electronics', 
            'Accessories', 
            'Phones', 
            'Vehicle Spare Parts', 
            'Grocery', 
            'Others'
        ];
        
        fetch('/api/inventory/categories')
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
            })
            .catch(error => {
                console.error('Error loading categories:', error);
                
                // Even if fetch fails, still load predefined categories
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
                    ${item.quantity <= 0 ? 
                      '<span class="badge bg-danger">Out of Stock</span>' : 
                      item.quantity <= 5 ? 
                      `<span class="badge bg-warning">${item.quantity}</span>` : 
                      item.quantity}
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
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to delete item: ' + error.message);
        });
    });
});
