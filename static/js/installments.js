
document.addEventListener('DOMContentLoaded', function() {
    // Initialize page
    loadDashboardData();
    loadCustomers();
    loadProducts();
    loadInstallmentSales();
    
    // Set default date to today
    document.getElementById('start-date').value = new Date().toISOString().split('T')[0];
    document.getElementById('payment-date').value = new Date().toISOString().split('T')[0];
    
    // Event listeners
    document.getElementById('add-new-customer').addEventListener('click', function(e) {
        e.preventDefault();
        toggleNewCustomerFields(true);
    });
    
    document.getElementById('product-select').addEventListener('change', updatePriceAndTotal);
    document.getElementById('quantity').addEventListener('input', updatePriceAndTotal);
    document.getElementById('down-payment').addEventListener('input', calculateMonthlyPayment);
    document.getElementById('installments-count').addEventListener('change', calculateMonthlyPayment);
    
    document.getElementById('save-installment').addEventListener('click', saveInstallmentSale);
    document.getElementById('save-payment').addEventListener('click', savePayment);
    document.getElementById('apply-filters').addEventListener('click', loadInstallmentSales);
    document.getElementById('recordPaymentBtn').addEventListener('click', function() {
        loadActiveInstallmentSales();
        new bootstrap.Modal(document.getElementById('paymentModal')).show();
    });
    
    document.getElementById('payment-installment-select').addEventListener('change', loadInstallmentNumbers);
});

function loadDashboardData() {
    fetch('/api/installment-sales/dashboard')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Error loading dashboard:', data.error);
                return;
            }
            
            // Update dashboard cards
            document.getElementById('active-sales-count').textContent = data.summary.total_active;
            document.getElementById('completed-sales-count').textContent = data.summary.total_completed;
            document.getElementById('overdue-sales-count').textContent = data.summary.total_overdue;
            document.getElementById('outstanding-balance').textContent = 'TZS ' + data.summary.outstanding_balance.toLocaleString();
            
            // Update upcoming payments table
            updateUpcomingPaymentsTable(data.upcoming_payments);
        })
        .catch(error => {
            console.error('Error loading dashboard data:', error);
        });
}

function loadCustomers() {
    fetch('/api/customers')
        .then(response => response.json())
        .then(customers => {
            const customerSelect = document.getElementById('customer-select');
            const customerFilter = document.getElementById('customer-filter');
            
            // Clear existing options
            customerSelect.innerHTML = '<option value="">Select Customer</option>';
            customerFilter.innerHTML = '<option value="">All Customers</option>';
            
            customers.forEach(customer => {
                const option = `<option value="${customer.id}">${customer.name} - ${customer.phone}</option>`;
                customerSelect.innerHTML += option;
                customerFilter.innerHTML += option;
            });
        })
        .catch(error => {
            console.error('Error loading customers:', error);
        });
}

function loadProducts() {
    fetch('/api/inventory')
        .then(response => response.json())
        .then(products => {
            const productSelect = document.getElementById('product-select');
            productSelect.innerHTML = '<option value="">Select Product</option>';
            
            products.forEach(product => {
                if (product.quantity > 0) {
                    const option = `<option value="${product.id}" data-price="${product.selling_price_retail || product.price}">${product.name} (Stock: ${product.quantity})</option>`;
                    productSelect.innerHTML += option;
                }
            });
        })
        .catch(error => {
            console.error('Error loading products:', error);
        });
}

function loadInstallmentSales() {
    let url = '/api/installment-sales';
    const params = new URLSearchParams();
    
    // Add filters
    const statusFilter = document.getElementById('status-filter').value;
    const customerFilter = document.getElementById('customer-filter').value;
    
    if (statusFilter) params.append('status', statusFilter);
    if (customerFilter) params.append('customer_id', customerFilter);
    
    if (params.toString()) {
        url += '?' + params.toString();
    }
    
    fetch(url)
        .then(response => response.json())
        .then(installmentSales => {
            updateInstallmentSalesTable(installmentSales);
        })
        .catch(error => {
            console.error('Error loading installment sales:', error);
        });
}

function loadActiveInstallmentSales() {
    fetch('/api/installment-sales?status=Active')
        .then(response => response.json())
        .then(installmentSales => {
            const select = document.getElementById('payment-installment-select');
            select.innerHTML = '<option value="">Select Installment Sale</option>';
            
            installmentSales.forEach(sale => {
                const option = `<option value="${sale.id}">${sale.customer_name} - ${sale.item_name} (Remaining: TZS ${sale.remaining_balance.toLocaleString()})</option>`;
                select.innerHTML += option;
            });
        })
        .catch(error => {
            console.error('Error loading active installment sales:', error);
        });
}

function loadInstallmentNumbers() {
    const saleId = document.getElementById('payment-installment-select').value;
    if (!saleId) return;
    
    fetch(`/api/installment-sales/${saleId}/payments`)
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('installment-number');
            const amountInput = document.getElementById('payment-amount');
            
            select.innerHTML = '<option value="">Select Installment</option>';
            
            data.payment_schedule.forEach(payment => {
                if (payment.status === 'Pending' || payment.status === 'Overdue') {
                    const option = `<option value="${payment.installment_number}" data-amount="${payment.amount_due}">Installment ${payment.installment_number} - Due: ${payment.due_date} (TZS ${payment.amount_due.toLocaleString()})</option>`;
                    select.innerHTML += option;
                }
            });
            
            // Set amount when installment is selected
            select.addEventListener('change', function() {
                const selectedOption = this.options[this.selectedIndex];
                if (selectedOption.dataset.amount) {
                    amountInput.value = selectedOption.dataset.amount;
                }
            });
        })
        .catch(error => {
            console.error('Error loading installment numbers:', error);
        });
}

function updateInstallmentSalesTable(installmentSales) {
    const tbody = document.querySelector('#installment-sales-table tbody');
    tbody.innerHTML = '';
    
    installmentSales.forEach(sale => {
        const statusBadge = getStatusBadge(sale.status);
        const row = `
            <tr>
                <td>${sale.customer_name}</td>
                <td>${sale.item_name} (${sale.quantity})</td>
                <td>TZS ${sale.total_amount.toLocaleString()}</td>
                <td>TZS ${sale.total_paid.toLocaleString()}</td>
                <td>TZS ${sale.remaining_balance.toLocaleString()}</td>
                <td>${statusBadge}</td>
                <td>${sale.next_due_date ? new Date(sale.next_due_date).toLocaleDateString() : 'N/A'}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="viewPaymentDetails(${sale.id})">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-success" onclick="recordQuickPayment(${sale.id})">
                        <i class="fas fa-credit-card"></i>
                    </button>
                    ${sale.status === 'Active' ? `<button class="btn btn-sm btn-warning" onclick="markOverdue(${sale.id})"><i class="fas fa-exclamation-triangle"></i></button>` : ''}
                </td>
            </tr>
        `;
        tbody.innerHTML += row;
    });
}

function updateUpcomingPaymentsTable(upcomingPayments) {
    const tbody = document.querySelector('#upcoming-payments-table tbody');
    tbody.innerHTML = '';
    
    upcomingPayments.forEach(payment => {
        const dueDate = new Date(payment.due_date);
        const isOverdue = dueDate < new Date();
        const dueDateClass = isOverdue ? 'text-danger' : '';
        
        const row = `
            <tr>
                <td>${payment.customer_name}</td>
                <td>${payment.item_name}</td>
                <td>TZS ${payment.amount_due.toLocaleString()}</td>
                <td class="${dueDateClass}">${dueDate.toLocaleDateString()}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="recordQuickPayment(${payment.installment_sale_id})">
                        Record Payment
                    </button>
                </td>
            </tr>
        `;
        tbody.innerHTML += row;
    });
}

function getStatusBadge(status) {
    const badges = {
        'Active': '<span class="badge bg-success">Active</span>',
        'Completed': '<span class="badge bg-primary">Completed</span>',
        'Overdue': '<span class="badge bg-danger">Overdue</span>',
        'Cancelled': '<span class="badge bg-secondary">Cancelled</span>'
    };
    return badges[status] || `<span class="badge bg-secondary">${status}</span>`;
}

function toggleNewCustomerFields(show) {
    const fields = document.getElementById('new-customer-fields');
    const customerSelect = document.getElementById('customer-select');
    
    if (show) {
        fields.style.display = 'block';
        customerSelect.disabled = true;
        customerSelect.required = false;
        document.getElementById('new-customer-name').required = true;
    } else {
        fields.style.display = 'none';
        customerSelect.disabled = false;
        customerSelect.required = true;
        document.getElementById('new-customer-name').required = false;
    }
}

function updatePriceAndTotal() {
    const productSelect = document.getElementById('product-select');
    const quantity = parseFloat(document.getElementById('quantity').value) || 1;
    const unitPriceInput = document.getElementById('unit-price');
    const totalAmountInput = document.getElementById('total-amount');
    
    const selectedOption = productSelect.options[productSelect.selectedIndex];
    if (selectedOption && selectedOption.dataset.price) {
        const unitPrice = parseFloat(selectedOption.dataset.price);
        unitPriceInput.value = unitPrice.toFixed(2);
        totalAmountInput.value = (unitPrice * quantity).toFixed(2);
        calculateMonthlyPayment();
    }
}

function calculateMonthlyPayment() {
    const totalAmount = parseFloat(document.getElementById('total-amount').value) || 0;
    const downPayment = parseFloat(document.getElementById('down-payment').value) || 0;
    const installmentsCount = parseInt(document.getElementById('installments-count').value) || 1;
    
    const remainingAmount = totalAmount - downPayment;
    const monthlyPayment = remainingAmount / installmentsCount;
    
    document.getElementById('monthly-payment').value = monthlyPayment.toFixed(2);
}

function saveInstallmentSale() {
    const form = document.getElementById('installment-form');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    let customerId = document.getElementById('customer-select').value;
    let customerData = null;
    
    // Check if creating new customer
    if (!customerId && document.getElementById('new-customer-fields').style.display === 'block') {
        customerData = {
            name: document.getElementById('new-customer-name').value,
            phone: document.getElementById('new-customer-phone').value,
            email: document.getElementById('new-customer-email').value,
            address: document.getElementById('new-customer-address').value
        };
    }
    
    const installmentData = {
        customer_id: customerId,
        customer_data: customerData,
        item_id: document.getElementById('product-select').value,
        quantity: parseInt(document.getElementById('quantity').value),
        total_amount: parseFloat(document.getElementById('total-amount').value),
        down_payment: parseFloat(document.getElementById('down-payment').value) || 0,
        number_of_installments: parseInt(document.getElementById('installments-count').value),
        start_date: document.getElementById('start-date').value,
        agreement_signed: document.getElementById('agreement-signed').checked,
        notes: document.getElementById('notes').value
    };
    
    // Create customer first if needed
    if (customerData) {
        fetch('/api/customers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(customerData)
        })
        .then(response => response.json())
        .then(customer => {
            installmentData.customer_id = customer.id;
            delete installmentData.customer_data;
            createInstallmentSale(installmentData);
        })
        .catch(error => {
            console.error('Error creating customer:', error);
            alert('Error creating customer');
        });
    } else {
        createInstallmentSale(installmentData);
    }
}

function createInstallmentSale(installmentData) {
    fetch('/api/installment-sales', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(installmentData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error: ' + data.error);
            return;
        }
        
        alert('Installment sale created successfully!');
        bootstrap.Modal.getInstance(document.getElementById('newInstallmentModal')).hide();
        document.getElementById('installment-form').reset();
        toggleNewCustomerFields(false);
        loadDashboardData();
        loadInstallmentSales();
    })
    .catch(error => {
        console.error('Error creating installment sale:', error);
        alert('Error creating installment sale');
    });
}

function savePayment() {
    const form = document.getElementById('payment-form');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    const saleId = document.getElementById('payment-installment-select').value;
    const paymentData = {
        installment_number: parseInt(document.getElementById('installment-number').value),
        payment_date: document.getElementById('payment-date').value,
        amount_paid: parseFloat(document.getElementById('payment-amount').value),
        payment_method: document.getElementById('payment-method').value,
        remarks: document.getElementById('payment-remarks').value
    };
    
    fetch(`/api/installment-sales/${saleId}/payments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(paymentData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error: ' + data.error);
            return;
        }
        
        alert('Payment recorded successfully!');
        bootstrap.Modal.getInstance(document.getElementById('paymentModal')).hide();
        document.getElementById('payment-form').reset();
        loadDashboardData();
        loadInstallmentSales();
    })
    .catch(error => {
        console.error('Error recording payment:', error);
        alert('Error recording payment');
    });
}

function viewPaymentDetails(saleId) {
    fetch(`/api/installment-sales/${saleId}/payments`)
        .then(response => response.json())
        .then(data => {
            const content = document.getElementById('payment-details-content');
            const sale = data.installment_sale;
            
            let html = `
                <div class="row mb-3">
                    <div class="col-md-6">
                        <h6>Sale Information</h6>
                        <p><strong>Customer:</strong> ${sale.customer_name}</p>
                        <p><strong>Product:</strong> ${sale.item_name} (${sale.quantity})</p>
                        <p><strong>Total Amount:</strong> TZS ${sale.total_amount.toLocaleString()}</p>
                        <p><strong>Status:</strong> ${getStatusBadge(sale.status)}</p>
                    </div>
                    <div class="col-md-6">
                        <h6>Payment Summary</h6>
                        <p><strong>Total Paid:</strong> TZS ${sale.total_paid.toLocaleString()}</p>
                        <p><strong>Remaining:</strong> TZS ${sale.remaining_balance.toLocaleString()}</p>
                        <p><strong>Next Due:</strong> ${sale.next_due_date ? new Date(sale.next_due_date).toLocaleDateString() : 'N/A'}</p>
                    </div>
                </div>
                
                <h6>Payment Schedule</h6>
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Installment</th>
                                <th>Due Date</th>
                                <th>Amount Due</th>
                                <th>Amount Paid</th>
                                <th>Payment Date</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            data.payment_schedule.forEach(payment => {
                const statusBadge = payment.status === 'Paid' ? '<span class="badge bg-success">Paid</span>' :
                                  payment.status === 'Overdue' ? '<span class="badge bg-danger">Overdue</span>' :
                                  '<span class="badge bg-warning">Pending</span>';
                
                html += `
                    <tr>
                        <td>${payment.installment_number}</td>
                        <td>${new Date(payment.due_date).toLocaleDateString()}</td>
                        <td>TZS ${payment.amount_due.toLocaleString()}</td>
                        <td>TZS ${payment.amount_paid.toLocaleString()}</td>
                        <td>${payment.payment_date ? new Date(payment.payment_date).toLocaleDateString() : '-'}</td>
                        <td>${statusBadge}</td>
                    </tr>
                `;
            });
            
            html += `
                        </tbody>
                    </table>
                </div>
            `;
            
            content.innerHTML = html;
            new bootstrap.Modal(document.getElementById('paymentDetailsModal')).show();
        })
        .catch(error => {
            console.error('Error loading payment details:', error);
        });
}

function recordQuickPayment(saleId) {
    document.getElementById('payment-installment-select').value = saleId;
    loadInstallmentNumbers();
    new bootstrap.Modal(document.getElementById('paymentModal')).show();
}

function markOverdue(saleId) {
    if (confirm('Mark this installment sale as overdue?')) {
        fetch(`/api/installment-sales/${saleId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: 'Overdue' })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error: ' + data.error);
                return;
            }
            
            loadDashboardData();
            loadInstallmentSales();
        })
        .catch(error => {
            console.error('Error updating status:', error);
        });
    }
}
