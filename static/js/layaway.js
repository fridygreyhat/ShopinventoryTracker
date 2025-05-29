
document.addEventListener('DOMContentLoaded', function() {
    let layawayPlans = [];

    // DOM Elements
    const layawayPlansTable = document.getElementById('layawayPlansTable');
    const statusFilter = document.getElementById('statusFilter');
    const customerFilter = document.getElementById('customerFilter');
    const dateFilter = document.getElementById('dateFilter');
    const filterLayawayPlansBtn = document.getElementById('filterLayawayPlans');
    const resetLayawayFiltersBtn = document.getElementById('resetLayawayFilters');
    const createLayawayPlanBtn = document.getElementById('createLayawayPlanBtn');
    const addPaymentBtn = document.getElementById('addPaymentBtn');

    // Initialize page
    loadLayawayPlans();

    // Event Listeners
    filterLayawayPlansBtn.addEventListener('click', loadLayawayPlans);
    resetLayawayFiltersBtn.addEventListener('click', resetFilters);
    createLayawayPlanBtn.addEventListener('click', createLayawayPlan);
    addPaymentBtn.addEventListener('click', addPayment);

    function loadLayawayPlans() {
        console.log('Loading layaway plans...');
        
        // Build query parameters
        const params = new URLSearchParams();
        
        if (statusFilter.value) {
            params.append('status', statusFilter.value);
        }
        
        if (customerFilter.value) {
            params.append('customer', customerFilter.value);
        }

        // Show loading state
        layawayPlansTable.innerHTML = '<tr><td colspan="8" class="text-center"><div class="spinner-border spinner-border-sm text-secondary" role="status"></div> Loading...</td></tr>';

        // Fetch layaway plans
        fetch(`/api/layaway?${params.toString()}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(plans => {
                console.log('Layaway plans loaded:', plans);
                layawayPlans = plans;
                displayLayawayPlans(plans);
                updateSummaryCards(plans);
            })
            .catch(error => {
                console.error('Error loading layaway plans:', error);
                layawayPlansTable.innerHTML = '<tr><td colspan="8" class="text-center text-danger">Error loading layaway plans</td></tr>';
            });
    }

    function displayLayawayPlans(plans) {
        if (plans.length === 0) {
            layawayPlansTable.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No layaway plans found</td></tr>';
            return;
        }

        let html = '';
        plans.forEach(plan => {
            const statusBadge = getStatusBadge(plan.status);
            const nextPaymentDate = plan.next_payment_date ? new Date(plan.next_payment_date).toLocaleDateString() : 'N/A';
            const remainingBalance = plan.remaining_balance || 0;
            const totalPaid = plan.total_paid || 0;

            html += `
                <tr>
                    <td>
                        <strong>#${plan.id}</strong>
                        <br><small class="text-muted">${new Date(plan.created_at).toLocaleDateString()}</small>
                    </td>
                    <td>
                        <strong>${plan.customer_name}</strong>
                        <br><small class="text-muted">${plan.customer_phone}</small>
                    </td>
                    <td>
                        <span class="currency-symbol">TZS</span> ${plan.total_amount.toLocaleString()}
                    </td>
                    <td>
                        <span class="currency-symbol">TZS</span> ${totalPaid.toLocaleString()}
                        <br><small class="text-muted">${plan.payments_count} payments</small>
                    </td>
                    <td>
                        <span class="currency-symbol">TZS</span> ${remainingBalance.toLocaleString()}
                    </td>
                    <td>${nextPaymentDate}</td>
                    <td>${statusBadge}</td>
                    <td>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-primary" onclick="viewPlanDetails(${plan.id})" title="View Details">
                                <i class="fas fa-eye"></i>
                            </button>
                            ${plan.status === 'active' ? `
                                <button class="btn btn-outline-success" onclick="showPaymentModal(${plan.id})" title="Add Payment">
                                    <i class="fas fa-plus"></i>
                                </button>
                            ` : ''}
                            <button class="btn btn-outline-secondary" onclick="printPlanStatement(${plan.id})" title="Print Statement">
                                <i class="fas fa-print"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        });

        layawayPlansTable.innerHTML = html;
    }

    function getStatusBadge(status) {
        const badges = {
            'active': '<span class="badge bg-warning">Active</span>',
            'completed': '<span class="badge bg-success">Completed</span>',
            'cancelled': '<span class="badge bg-danger">Cancelled</span>',
            'defaulted': '<span class="badge bg-dark">Defaulted</span>'
        };
        return badges[status] || '<span class="badge bg-secondary">Unknown</span>';
    }

    function updateSummaryCards(plans) {
        const activePlans = plans.filter(p => p.status === 'active').length;
        const completedPlans = plans.filter(p => p.status === 'completed').length;
        const overduePlans = plans.filter(p => {
            if (p.status !== 'active' || !p.next_payment_date) return false;
            return new Date(p.next_payment_date) < new Date();
        }).length;
        const totalValue = plans.reduce((sum, p) => sum + p.total_amount, 0);

        document.getElementById('activePlansCount').textContent = activePlans;
        document.getElementById('completedPlansCount').textContent = completedPlans;
        document.getElementById('overduePlansCount').textContent = overduePlans;
        document.getElementById('totalLayawayValue').textContent = totalValue.toLocaleString();
    }

    function resetFilters() {
        statusFilter.value = '';
        customerFilter.value = '';
        dateFilter.value = '';
        loadLayawayPlans();
    }

    function createLayawayPlan() {
        const customerName = document.getElementById('newLayawayCustomerName').value;
        const customerPhone = document.getElementById('newLayawayCustomerPhone').value;
        const totalAmount = parseFloat(document.getElementById('newLayawayTotalAmount').value);
        const downPayment = parseFloat(document.getElementById('newLayawayDownPayment').value) || 0;
        const installmentAmount = parseFloat(document.getElementById('newLayawayInstallmentAmount').value);
        const frequency = document.getElementById('newLayawayFrequency').value;
        const notes = document.getElementById('newLayawayNotes').value;

        if (!customerName || !customerPhone || !totalAmount || !installmentAmount) {
            alert('Please fill in all required fields');
            return;
        }

        const planData = {
            customer_name: customerName,
            customer_phone: customerPhone,
            total_amount: totalAmount,
            down_payment: downPayment,
            installment_amount: installmentAmount,
            payment_frequency: frequency,
            notes: notes
        };

        fetch('/api/layaway', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(planData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.id) {
                alert('Layaway plan created successfully!');
                
                // Close modal and reset form
                const modal = bootstrap.Modal.getInstance(document.getElementById('createLayawayModal'));
                modal.hide();
                document.getElementById('createLayawayForm').reset();
                
                // Reload plans
                loadLayawayPlans();
            } else {
                alert('Error creating layaway plan: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error creating layaway plan:', error);
            alert('Failed to create layaway plan');
        });
    }

    function showPaymentModal(planId) {
        document.getElementById('paymentPlanId').value = planId;
        const modal = new bootstrap.Modal(document.getElementById('paymentModal'));
        modal.show();
    }

    function addPayment() {
        const planId = document.getElementById('paymentPlanId').value;
        const amount = parseFloat(document.getElementById('paymentAmount').value);
        const method = document.getElementById('paymentMethod').value;
        const reference = document.getElementById('paymentReference').value;
        const notes = document.getElementById('paymentNotes').value;

        if (!amount || amount <= 0) {
            alert('Please enter a valid payment amount');
            return;
        }

        const paymentData = {
            amount: amount,
            payment_method: method,
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
            if (data.payment) {
                alert('Payment added successfully!');
                
                // Close modal and reset form
                const modal = bootstrap.Modal.getInstance(document.getElementById('paymentModal'));
                modal.hide();
                document.getElementById('addPaymentForm').reset();
                
                // Reload plans
                loadLayawayPlans();
            } else {
                alert('Error adding payment: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error adding payment:', error);
            alert('Failed to add payment');
        });
    }

    function viewPlanDetails(planId) {
        const plan = layawayPlans.find(p => p.id === planId);
        if (!plan) return;

        alert(`Plan Details:\n\nCustomer: ${plan.customer_name}\nTotal: TZS ${plan.total_amount.toLocaleString()}\nPaid: TZS ${(plan.total_paid || 0).toLocaleString()}\nRemaining: TZS ${plan.remaining_balance.toLocaleString()}\nStatus: ${plan.status}`);
    }

    function printPlanStatement(planId) {
        alert('Print statement functionality would be implemented here');
    }

    // Make functions globally available
    window.viewPlanDetails = viewPlanDetails;
    window.showPaymentModal = showPaymentModal;
    window.printPlanStatement = printPlanStatement;
});
