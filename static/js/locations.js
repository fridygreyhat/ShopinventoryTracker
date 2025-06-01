
// Location Management JavaScript
let currentLocations = [];
let currentTransfers = [];
let transferItemCounter = 0;

document.addEventListener('DOMContentLoaded', function() {
    loadLocations();
    loadTransfers();
    setupEventListeners();
});

function setupEventListeners() {
    // Add location form
    document.getElementById('addLocationForm').addEventListener('submit', function(e) {
        e.preventDefault();
        saveLocation();
    });

    // Create transfer form
    document.getElementById('createTransferForm').addEventListener('submit', function(e) {
        e.preventDefault();
        createTransfer();
    });

    // Transfer filters
    document.getElementById('transferStatusFilter').addEventListener('change', filterTransfers);
    document.getElementById('transferFromDate').addEventListener('change', filterTransfers);
    document.getElementById('transferToDate').addEventListener('change', filterTransfers);

    // Location selects change handler
    document.getElementById('transferFromLocation').addEventListener('change', function() {
        populateLocationItems(this.value);
    });
}

function loadLocations() {
    fetch('/api/locations')
        .then(response => response.json())
        .then(data => {
            currentLocations = data;
            displayLocations(data);
            populateLocationSelects();
        })
        .catch(error => {
            console.error('Error loading locations:', error);
            showAlert('Error loading locations', 'danger');
        });
}

function displayLocations(locations) {
    const container = document.getElementById('locationsContainer');
    
    if (locations.length === 0) {
        container.innerHTML = `
            <div class="col-12">
                <div class="card text-center">
                    <div class="card-body">
                        <i class="fas fa-warehouse fa-3x text-muted mb-3"></i>
                        <h5>No Locations Found</h5>
                        <p class="text-muted">Create your first location to start tracking inventory by location.</p>
                        <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addLocationModal">
                            <i class="fas fa-plus"></i> Add First Location
                        </button>
                    </div>
                </div>
            </div>
        `;
        return;
    }

    container.innerHTML = locations.map(location => `
        <div class="col-lg-6 col-xl-4 mb-4">
            <div class="card h-100 ${location.is_default ? 'border-primary' : ''}">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-0">${location.name} ${location.is_default ? '<span class="badge bg-primary ms-2">Default</span>' : ''}</h6>
                        <small class="text-muted">${location.code} • ${location.type}</small>
                    </div>
                    <div class="dropdown">
                        <button class="btn btn-sm btn-outline-secondary" type="button" data-bs-toggle="dropdown">
                            <i class="fas fa-ellipsis-v"></i>
                        </button>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="#" onclick="viewLocationStock(${location.id})">
                                <i class="fas fa-boxes"></i> View Stock
                            </a></li>
                            <li><a class="dropdown-item" href="#" onclick="editLocation(${location.id})">
                                <i class="fas fa-edit"></i> Edit
                            </a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item text-danger" href="#" onclick="deleteLocation(${location.id})">
                                <i class="fas fa-trash"></i> Delete
                            </a></li>
                        </ul>
                    </div>
                </div>
                <div class="card-body">
                    <div class="row text-center">
                        <div class="col-6">
                            <div class="border-end">
                                <h4 class="text-primary mb-0">${location.total_items}</h4>
                                <small class="text-muted">Items</small>
                            </div>
                        </div>
                        <div class="col-6">
                            <h4 class="text-success mb-0">${location.total_stock.toLocaleString()}</h4>
                            <small class="text-muted">Total Stock</small>
                        </div>
                    </div>
                    
                    ${location.address ? `
                        <div class="mt-3">
                            <small class="text-muted">
                                <i class="fas fa-map-marker-alt"></i> ${location.address}
                                ${location.city ? `, ${location.city}` : ''}
                            </small>
                        </div>
                    ` : ''}
                    
                    ${location.manager_name ? `
                        <div class="mt-2">
                            <small class="text-muted">
                                <i class="fas fa-user"></i> ${location.manager_name}
                            </small>
                        </div>
                    ` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

function populateLocationSelects() {
    const fromSelect = document.getElementById('transferFromLocation');
    const toSelect = document.getElementById('transferToLocation');
    
    const options = currentLocations.map(location => 
        `<option value="${location.id}">${location.name} (${location.code})</option>`
    ).join('');
    
    fromSelect.innerHTML = '<option value="">Select source location...</option>' + options;
    toSelect.innerHTML = '<option value="">Select destination location...</option>' + options;
}

function saveLocation() {
    const form = document.getElementById('addLocationForm');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    // Convert checkbox
    data.is_default = document.getElementById('locationDefault').checked;
    
    fetch('/api/locations', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showAlert(data.error, 'danger');
        } else {
            showAlert('Location created successfully', 'success');
            bootstrap.Modal.getInstance(document.getElementById('addLocationModal')).hide();
            form.reset();
            loadLocations();
        }
    })
    .catch(error => {
        console.error('Error saving location:', error);
        showAlert('Error saving location', 'danger');
    });
}

function viewLocationStock(locationId) {
    const location = currentLocations.find(l => l.id === locationId);
    if (!location) return;
    
    document.getElementById('locationStockModalTitle').textContent = `Stock at ${location.name}`;
    
    fetch(`/api/locations/${locationId}/stock`)
        .then(response => response.json())
        .then(data => {
            displayLocationStock(data);
            new bootstrap.Modal(document.getElementById('locationStockModal')).show();
        })
        .catch(error => {
            console.error('Error loading location stock:', error);
            showAlert('Error loading stock data', 'danger');
        });
}

function displayLocationStock(stockItems) {
    const table = document.getElementById('locationStockTable');
    
    if (stockItems.length === 0) {
        table.innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-muted">No stock items found for this location</td>
            </tr>
        `;
        return;
    }
    
    table.innerHTML = stockItems.map(stockItem => `
        <tr>
            <td>${stockItem.item.name}</td>
            <td>${stockItem.item.sku || '-'}</td>
            <td>${stockItem.quantity}</td>
            <td>${stockItem.available_quantity}</td>
            <td>${stockItem.reserved_quantity}</td>
            <td>${stockItem.min_stock_level}</td>
            <td>${stockItem.max_stock_level}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="editLocationStock(${stockItem.id})">
                    <i class="fas fa-edit"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function loadTransfers() {
    fetch('/api/transfers')
        .then(response => response.json())
        .then(data => {
            currentTransfers = data;
            displayTransfers(data);
        })
        .catch(error => {
            console.error('Error loading transfers:', error);
            showAlert('Error loading transfers', 'danger');
        });
}

function displayTransfers(transfers) {
    const table = document.getElementById('transfersTable');
    
    if (transfers.length === 0) {
        table.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted">No transfers found</td>
            </tr>
        `;
        return;
    }
    
    table.innerHTML = transfers.map(transfer => `
        <tr>
            <td>
                <strong>${transfer.transfer_number}</strong>
                ${transfer.notes ? `<br><small class="text-muted">${transfer.notes}</small>` : ''}
            </td>
            <td>${transfer.from_location_name} (${transfer.from_location_code})</td>
            <td>${transfer.to_location_name} (${transfer.to_location_code})</td>
            <td>
                <span class="badge bg-info">${transfer.items_count} items</span>
                <br><small class="text-muted">${transfer.total_quantity} total qty</small>
            </td>
            <td>${getStatusBadge(transfer.status)}</td>
            <td>${new Date(transfer.transfer_date).toLocaleDateString()}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="viewTransferDetails(${transfer.id})">
                        <i class="fas fa-eye"></i>
                    </button>
                    ${transfer.status === 'pending' ? `
                        <button class="btn btn-outline-success" onclick="approveTransfer(${transfer.id})">
                            <i class="fas fa-check"></i>
                        </button>
                        <button class="btn btn-outline-danger" onclick="cancelTransfer(${transfer.id})">
                            <i class="fas fa-times"></i>
                        </button>
                    ` : ''}
                    ${transfer.status === 'in_transit' ? `
                        <button class="btn btn-outline-success" onclick="completeTransfer(${transfer.id})">
                            <i class="fas fa-check-circle"></i>
                        </button>
                    ` : ''}
                </div>
            </td>
        </tr>
    `).join('');
}

function getStatusBadge(status) {
    const badges = {
        'pending': 'bg-warning',
        'in_transit': 'bg-info',
        'completed': 'bg-success',
        'cancelled': 'bg-danger'
    };
    
    return `<span class="badge ${badges[status] || 'bg-secondary'}">${status.replace('_', ' ')}</span>`;
}

function filterTransfers() {
    const status = document.getElementById('transferStatusFilter').value;
    const fromDate = document.getElementById('transferFromDate').value;
    const toDate = document.getElementById('transferToDate').value;
    
    let filtered = currentTransfers;
    
    if (status) {
        filtered = filtered.filter(t => t.status === status);
    }
    
    if (fromDate) {
        filtered = filtered.filter(t => t.transfer_date >= fromDate);
    }
    
    if (toDate) {
        filtered = filtered.filter(t => t.transfer_date <= toDate);
    }
    
    displayTransfers(filtered);
}

function resetTransferFilters() {
    document.getElementById('transferStatusFilter').value = '';
    document.getElementById('transferFromDate').value = '';
    document.getElementById('transferToDate').value = '';
    displayTransfers(currentTransfers);
}

function addTransferItem() {
    const container = document.getElementById('transferItemsContainer');
    const itemId = `transfer-item-${transferItemCounter++}`;
    
    const itemHtml = `
        <div class="row mb-3 transfer-item" id="${itemId}">
            <div class="col-md-4">
                <select class="form-select item-select" name="items[${transferItemCounter}][item_id]" required>
                    <option value="">Select item...</option>
                </select>
            </div>
            <div class="col-md-3">
                <input type="number" class="form-control" name="items[${transferItemCounter}][quantity]" 
                       placeholder="Quantity" min="1" required>
            </div>
            <div class="col-md-4">
                <input type="text" class="form-control" name="items[${transferItemCounter}][notes]" 
                       placeholder="Notes (optional)">
            </div>
            <div class="col-md-1">
                <button type="button" class="btn btn-outline-danger" onclick="removeTransferItem('${itemId}')">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', itemHtml);
}

function removeTransferItem(itemId) {
    document.getElementById(itemId).remove();
}

function populateLocationItems(locationId) {
    if (!locationId) return;
    
    fetch(`/api/locations/${locationId}/stock`)
        .then(response => response.json())
        .then(data => {
            const selects = document.querySelectorAll('.item-select');
            const options = data.map(stockItem => 
                `<option value="${stockItem.item_id}" data-available="${stockItem.available_quantity}">
                    ${stockItem.item.name} (Available: ${stockItem.available_quantity})
                </option>`
            ).join('');
            
            selects.forEach(select => {
                select.innerHTML = '<option value="">Select item...</option>' + options;
            });
        })
        .catch(error => {
            console.error('Error loading location items:', error);
        });
}

function createTransfer() {
    const form = document.getElementById('createTransferForm');
    const formData = new FormData(form);
    
    // Build transfer data
    const data = {
        from_location_id: parseInt(formData.get('from_location_id')),
        to_location_id: parseInt(formData.get('to_location_id')),
        requested_by: formData.get('requested_by'),
        expected_arrival: formData.get('expected_arrival'),
        notes: formData.get('notes'),
        items: []
    };
    
    // Collect items
    const transferItems = document.querySelectorAll('.transfer-item');
    transferItems.forEach(item => {
        const itemId = item.querySelector('select').value;
        const quantity = item.querySelector('input[type="number"]').value;
        const notes = item.querySelector('input[type="text"]').value;
        
        if (itemId && quantity) {
            data.items.push({
                item_id: parseInt(itemId),
                quantity: parseInt(quantity),
                notes: notes
            });
        }
    });
    
    if (data.items.length === 0) {
        showAlert('Please add at least one item to transfer', 'warning');
        return;
    }
    
    fetch('/api/transfers', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showAlert(data.error, 'danger');
        } else {
            showAlert('Transfer created successfully', 'success');
            bootstrap.Modal.getInstance(document.getElementById('createTransferModal')).hide();
            form.reset();
            document.getElementById('transferItemsContainer').innerHTML = '';
            transferItemCounter = 0;
            loadTransfers();
        }
    })
    .catch(error => {
        console.error('Error creating transfer:', error);
        showAlert('Error creating transfer', 'danger');
    });
}

function updateTransferStatus(transferId, status, approvedBy = null) {
    const data = { status };
    if (approvedBy) {
        data.approved_by = approvedBy;
    }
    
    fetch(`/api/transfers/${transferId}/status`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showAlert(data.error, 'danger');
        } else {
            showAlert(`Transfer ${status} successfully`, 'success');
            loadTransfers();
        }
    })
    .catch(error => {
        console.error('Error updating transfer:', error);
        showAlert('Error updating transfer', 'danger');
    });
}

function approveTransfer(transferId) {
    const approvedBy = prompt('Enter your name for approval:');
    if (approvedBy) {
        updateTransferStatus(transferId, 'in_transit', approvedBy);
    }
}

function completeTransfer(transferId) {
    if (confirm('Mark this transfer as completed? This will move the stock between locations.')) {
        updateTransferStatus(transferId, 'completed');
    }
}

function cancelTransfer(transferId) {
    if (confirm('Cancel this transfer? This action cannot be undone.')) {
        updateTransferStatus(transferId, 'cancelled');
    }
}

function deleteLocation(locationId) {
    if (confirm('Are you sure you want to delete this location? This action cannot be undone.')) {
        fetch(`/api/locations/${locationId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showAlert(data.error, 'danger');
            } else {
                showAlert('Location deleted successfully', 'success');
                loadLocations();
            }
        })
        .catch(error => {
            console.error('Error deleting location:', error);
            showAlert('Error deleting location', 'danger');
        });
    }
}

function showAlert(message, type = 'info') {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    const container = document.querySelector('.container');
    container.insertAdjacentHTML('afterbegin', alertHtml);
    
    // Auto dismiss after 5 seconds
    setTimeout(() => {
        const alert = container.querySelector('.alert');
        if (alert) {
            bootstrap.Alert.getInstance(alert)?.close();
        }
    }, 5000);
}
