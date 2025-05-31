
document.addEventListener('DOMContentLoaded', function() {
    loadPlans();
    
    // Set today's date as default for payment date
    document.getElementById('paymentDate').valueAsDate = new Date();
    
    // Search functionality
    document.getElementById('searchBtn').addEventListener('click', function() {
        const searchTerm = document.getElementById('searchInput').value;
        loadPlans(searchTerm);
    });
    
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            const searchTerm = this.value;
            loadPlans(searchTerm);
        }
    });
    
    // Filter functionality
    document.querySelectorAll('[data-filter]').forEach(filter => {
        filter.addEventListener('click', function(e) {
            e.preventDefault();
            const filterType = this.getAttribute('data-filter');
            loadPlans('', filterType);
        });
    });
});

function loadPlans(search = '', filter = 'all') {
    const tableBody = document.getElementById('plansTable');
    tableBody.innerHTML = '<tr><td colspan="8" class="text-center"><div class="spinner-border text-primary" role="status"></div></td></tr>';
    
    let url = '/api/layaway';
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (filter !== 'all') params.append('status', filter);
    
    if (params.toString()) {
        url += '?' + params.toString();
    }
    
    fetch(url)
        .then(response => response.json())
        .then(plans => {
            displayPlans(plans);
            updateSummaryCards(plans);
        })
        .catch(error => {
            console.error('Error loading plans:', error);
            tableBody.innerHTML = '<tr><td colspan="8" class="text-center text-danger">Error loading plans</td></tr>';
        });
}

function displayPlans(plans) {
    const tableBody = document.getElementById('plansTable');
    
    if (plans.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No payment plans found</td></tr>';
        return;
    }
    
    tableBody.innerHTML = plans.map(plan => {
        const statusBadge = getStatusBadge(plan.status);
        const nextPaymentDate = plan.next_payment_date ? 
            new Date(plan.next_payment_date).toLocaleDateString() : 'N/A';
        
        return `
            <tr>
                <td>
                    <strong>${plan.customer_name}</strong>
                    ${plan.customer_email ? `<br><small class="text-muted">${plan.customer_email}</small>` : ''}
                </td>
                <td>${plan.customer_phone || 'N/A'}</td>
                <td>TZS ${plan.total_amount.toLocaleString()}</td>
                <td>TZS ${plan.down_payment.toLocaleString()}</td>
                <td>TZS ${plan.remaining_balance.toLocaleString()}</td>
                <td>${nextPaymentDate}</td>
                <td>${statusBadge}</td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button type="button" class="btn btn-outline-primary" onclick="viewPlanDetails(${plan.id})" title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        ${plan.status === 'active' ? `
                            <button type="button" class="btn btn-outline-success" onclick="recordPaymentModal(${plan.id})" title="Record Payment">
                                <i class="fas fa-plus"></i>
                            </button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function getStatusBadge(status) {
    const badges = {
        'active': '<span class="badge bg-success">Active</span>',
        'completed': '<span class="badge bg-primary">Completed</span>',
        'cancelled': '<span class="badge bg-danger">Cancelled</span>',
        'overdue': '<span class="badge bg-warning">Overdue</span>'
    };
    return badges[status] || '<span class="badge bg-secondary">Unknown</span>';
}

function updateSummaryCards(plans) {
    const activePlans = plans.filter(plan => plan.status === 'active').length;
    const totalAmount = plans.reduce((sum, plan) => sum + plan.total_amount, 0);
    const overduePlans = plans.filter(plan => {
        if (plan.status !== 'active' || !plan.next_payment_date) return false;
        return new Date(plan.next_payment_date) < new Date();
    }).length;
    
    // Calculate this month's plans (next payment in current month)
    const currentMonth = new Date().getMonth();
    const currentYear = new Date().getFullYear();
    const thisMonthPlans = plans.filter(plan => {
        if (!plan.next_payment_date) return false;
        const paymentDate = new Date(plan.next_payment_date);
        return paymentDate.getMonth() === currentMonth && paymentDate.getFullYear() === currentYear;
    }).length;
    
    document.getElementById('activePlansCount').textContent = activePlans;
    document.getElementById('totalAmount').textContent = `TZS ${totalAmount.toLocaleString()}`;
    document.getElementById('overduePlansCount').textContent = overduePlans;
    document.getElementById('thisMonthCount').textContent = thisMonthPlans;
}

function recordPaymentModal(planId) {
    document.getElementById('paymentPlanId').value = planId;
    document.getElementById('paymentForm').reset();
    document.getElementById('paymentDate').valueAsDate = new Date();
    
    const modal = new bootstrap.Modal(document.getElementById('paymentModal'));
    modal.show();
}

function recordPayment() {
    const planId = document.getElementById('paymentPlanId').value;
    const amount = parseFloat(document.getElementById('paymentAmount').value);
    const paymentMethod = document.getElementById('paymentMethodModal').value;
    const paymentDate = document.getElementById('paymentDate').value;
    const reference = document.getElementById('paymentReference').value;
    const notes = document.getElementById('paymentNotes').value;
    
    if (!amount || amount <= 0) {
        alert('Please enter a valid payment amount');
        return;
    }
    
    const paymentData = {
        amount: amount,
        payment_method: paymentMethod,
        payment_date: paymentDate,
        reference_number: reference,
        notes: notes
    };
    
    fetch(`/api/layaway/${planId}/payment`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(paymentData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.id) {
            alert('Payment recorded successfully!');
            bootstrap.Modal.getInstance(document.getElementById('paymentModal')).hide();
            loadPlans();
            document.getElementById('paymentForm').reset();
        } else {
            alert('Error recording payment: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error recording payment:', error);
        alert('Failed to record payment');
    });
}

function viewPlanDetails(planId) {
    fetch(`/api/layaway/${planId}`)
        .then(response => response.json())
        .then(plan => {
            const content = document.getElementById('planDetailsContent');
            
            let itemsHtml = '';
            if (plan.items && plan.items.length > 0) {
                itemsHtml = `
                    <h6>Items:</h6>
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Item</th>
                                    <th>SKU</th>
                                    <th>Price</th>
                                    <th>Qty</th>
                                    <th>Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${plan.items.map(item => `
                                    <tr>
                                        <td>${item.name}</td>
                                        <td>${item.sku || 'N/A'}</td>
                                        <td>TZS ${item.price.toLocaleString()}</td>
                                        <td>${item.quantity}</td>
                                        <td>TZS ${item.total.toLocaleString()}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `;
            }
            
            content.innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <h6>Customer Information:</h6>
                        <p><strong>Name:</strong> ${plan.customer_name}</p>
                        <p><strong>Phone:</strong> ${plan.customer_phone || 'N/A'}</p>
                        <p><strong>Email:</strong> ${plan.customer_email || 'N/A'}</p>
                    </div>
                    <div class="col-md-6">
                        <h6>Payment Information:</h6>
                        <p><strong>Total Amount:</strong> TZS ${plan.total_amount.toLocaleString()}</p>
                        <p><strong>Down Payment:</strong> TZS ${plan.down_payment.toLocaleString()}</p>
                        <p><strong>Remaining Balance:</strong> TZS ${plan.remaining_balance.toLocaleString()}</p>
                        <p><strong>Installment Amount:</strong> TZS ${plan.installment_amount.toLocaleString()}</p>
                        <p><strong>Payment Frequency:</strong> ${plan.payment_frequency}</p>
                        <p><strong>Next Payment:</strong> ${plan.next_payment_date ? new Date(plan.next_payment_date).toLocaleDateString() : 'N/A'}</p>
                        <p><strong>Status:</strong> ${getStatusBadge(plan.status)}</p>
                        <p><strong>Total Paid:</strong> TZS ${plan.total_paid.toLocaleString()}</p>
                        <p><strong>Payments Made:</strong> ${plan.payments_count}</p>
                    </div>
                </div>
                ${itemsHtml}
                ${plan.notes ? `<div class="mt-3"><h6>Notes:</h6><p>${plan.notes}</p></div>` : ''}
            `;
            
            const modal = new bootstrap.Modal(document.getElementById('planDetailsModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error loading plan details:', error);
            alert('Failed to load plan details');
        });
}
