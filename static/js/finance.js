document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    const filterBtn = document.getElementById('filter-btn');
    const yearSelect = document.getElementById('year-select');
    
    // Transaction tables
    const allTransactionsTable = document.getElementById('all-transactions-table');
    const incomeTransactionsTable = document.getElementById('income-transactions-table');
    const expenseTransactionsTable = document.getElementById('expense-transactions-table');
    
    // Transaction form elements
    const transactionForm = document.getElementById('transaction-form');
    const transactionId = document.getElementById('transaction-id');
    const transactionDate = document.getElementById('transaction-date');
    const transactionDescription = document.getElementById('transaction-description');
    const transactionAmount = document.getElementById('transaction-amount');
    const transactionType = document.getElementById('transaction-type');
    const transactionCategory = document.getElementById('transaction-category');
    const transactionPaymentMethod = document.getElementById('transaction-payment-method');
    const transactionReference = document.getElementById('transaction-reference');
    const transactionNotes = document.getElementById('transaction-notes');
    
    // Modal elements
    const transactionModal = new bootstrap.Modal(document.getElementById('transactionModal'));
    const transactionModalLabel = document.getElementById('transactionModalLabel');
    const deleteConfirmModal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
    
    // Buttons
    const saveTransactionBtn = document.getElementById('save-transaction-btn');
    const deleteTransactionBtn = document.getElementById('delete-transaction-btn');
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    
    // Summary elements
    const incomeValue = document.getElementById('income-value');
    const expensesValue = document.getElementById('expenses-value');
    const profitValue = document.getElementById('profit-value');
    
    // Declare chart globally
    let monthlyChart = null;
    
    // Set default dates (current month)
    const today = new Date();
    const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    
    // Format dates for input fields
    startDateInput.value = formatDateForInput(firstDayOfMonth);
    endDateInput.value = formatDateForInput(today);
    
    // Populate year select for monthly chart
    populateYearSelect();
    
    // Populate categories
    loadCategories();
    
    // Load initial data
    loadTransactions();
    loadMonthlySummary();
    
    // Event listeners
    filterBtn.addEventListener('click', loadTransactions);
    yearSelect.addEventListener('change', loadMonthlySummary);
    
    document.getElementById('add-transaction-btn').addEventListener('click', function() {
        resetTransactionForm();
        transactionModalLabel.textContent = 'Add Transaction';
        deleteTransactionBtn.style.display = 'none';
        transactionDate.value = formatDateForInput(new Date());
    });
    
    saveTransactionBtn.addEventListener('click', saveTransaction);
    deleteTransactionBtn.addEventListener('click', function() {
        deleteConfirmModal.show();
    });
    
    confirmDeleteBtn.addEventListener('click', function() {
        deleteTransaction(transactionId.value);
    });
    
    // Load transaction data with optional date filters
    function loadTransactions() {
        const startDate = startDateInput.value;
        const endDate = endDateInput.value;
        
        let url = '/api/finance/transactions';
        const params = [];
        
        if (startDate) {
            params.push(`start_date=${startDate}`);
        }
        
        if (endDate) {
            params.push(`end_date=${endDate}`);
        }
        
        if (params.length > 0) {
            url += '?' + params.join('&');
        }
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                displayTransactions(data.transactions);
                updateFinancialSummary(data.summary);
            })
            .catch(error => {
                console.error('Error loading transactions:', error);
                allTransactionsTable.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Error loading transactions</td></tr>';
                incomeTransactionsTable.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error loading income transactions</td></tr>';
                expenseTransactionsTable.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error loading expense transactions</td></tr>';
            });
    }
    
    // Load monthly summary data for charts
    function loadMonthlySummary() {
        const year = yearSelect.value;
        fetch(`/api/finance/summaries/monthly?year=${year}`)
            .then(response => response.json())
            .then(data => {
                createMonthlyChart(data);
            })
            .catch(error => {
                console.error('Error loading monthly summary:', error);
            });
    }
    
    // Load categories for transaction form
    function loadCategories() {
        fetch('/api/finance/categories')
            .then(response => response.json())
            .then(categories => {
                transactionCategory.innerHTML = '<option value="">Select Category</option>';
                
                categories.forEach(category => {
                    const option = document.createElement('option');
                    option.value = category;
                    option.textContent = category;
                    transactionCategory.appendChild(option);
                });
            })
            .catch(error => {
                console.error('Error loading categories:', error);
            });
    }
    
    // Display transactions in their respective tables
    function displayTransactions(transactions) {
        // Filter transactions by type
        const incomeTransactions = transactions.filter(t => t.transaction_type === 'Income');
        const expenseTransactions = transactions.filter(t => t.transaction_type === 'Expense');
        
        // Display all transactions
        if (transactions.length === 0) {
            allTransactionsTable.innerHTML = '<tr><td colspan="6" class="text-center">No transactions found for the selected period</td></tr>';
        } else {
            let allHtml = '';
            
            transactions.forEach(transaction => {
                const amountClass = transaction.transaction_type === 'Income' ? 'text-success' : 'text-danger';
                const amountPrefix = transaction.transaction_type === 'Income' ? '+' : '-';
                
                allHtml += `
                <tr>
                    <td>${formatDate(transaction.date)}</td>
                    <td>${transaction.description}</td>
                    <td>${transaction.category}</td>
                    <td class="${amountClass}">
                        ${amountPrefix} <span class="currency-symbol">TZS</span> ${transaction.amount.toLocaleString()}
                    </td>
                    <td>
                        <span class="badge bg-${transaction.transaction_type === 'Income' ? 'success' : 'danger'}">
                            ${transaction.transaction_type}
                        </span>
                    </td>
                    <td>
                        <button class="btn btn-sm btn-primary edit-transaction-btn" data-id="${transaction.id}">
                            <i class="fas fa-edit"></i>
                        </button>
                    </td>
                </tr>
                `;
            });
            
            allTransactionsTable.innerHTML = allHtml;
        }
        
        // Display income transactions
        if (incomeTransactions.length === 0) {
            incomeTransactionsTable.innerHTML = '<tr><td colspan="5" class="text-center">No income transactions found for the selected period</td></tr>';
        } else {
            let incomeHtml = '';
            
            incomeTransactions.forEach(transaction => {
                incomeHtml += `
                <tr>
                    <td>${formatDate(transaction.date)}</td>
                    <td>${transaction.description}</td>
                    <td>${transaction.category}</td>
                    <td class="text-success">
                        <span class="currency-symbol">TZS</span> ${transaction.amount.toLocaleString()}
                    </td>
                    <td>
                        <button class="btn btn-sm btn-primary edit-transaction-btn" data-id="${transaction.id}">
                            <i class="fas fa-edit"></i>
                        </button>
                    </td>
                </tr>
                `;
            });
            
            incomeTransactionsTable.innerHTML = incomeHtml;
        }
        
        // Display expense transactions
        if (expenseTransactions.length === 0) {
            expenseTransactionsTable.innerHTML = '<tr><td colspan="5" class="text-center">No expense transactions found for the selected period</td></tr>';
        } else {
            let expenseHtml = '';
            
            expenseTransactions.forEach(transaction => {
                expenseHtml += `
                <tr>
                    <td>${formatDate(transaction.date)}</td>
                    <td>${transaction.description}</td>
                    <td>${transaction.category}</td>
                    <td class="text-danger">
                        <span class="currency-symbol">TZS</span> ${transaction.amount.toLocaleString()}
                    </td>
                    <td>
                        <button class="btn btn-sm btn-primary edit-transaction-btn" data-id="${transaction.id}">
                            <i class="fas fa-edit"></i>
                        </button>
                    </td>
                </tr>
                `;
            });
            
            expenseTransactionsTable.innerHTML = expenseHtml;
        }
        
        // Add event listeners to edit buttons
        document.querySelectorAll('.edit-transaction-btn').forEach(button => {
            button.addEventListener('click', function() {
                const id = this.getAttribute('data-id');
                editTransaction(id);
            });
        });
    }
    
    // Update financial summary display
    function updateFinancialSummary(summary) {
        incomeValue.textContent = summary.total_income.toLocaleString();
        expensesValue.textContent = summary.total_expenses.toLocaleString();
        profitValue.textContent = summary.net_profit.toLocaleString();
        
        // Add color to profit based on value
        if (summary.net_profit > 0) {
            profitValue.classList.add('text-success');
            profitValue.classList.remove('text-danger');
        } else if (summary.net_profit < 0) {
            profitValue.classList.add('text-danger');
            profitValue.classList.remove('text-success');
        } else {
            profitValue.classList.remove('text-success');
            profitValue.classList.remove('text-danger');
        }
    }
    
    // Create monthly chart
    function createMonthlyChart(data) {
        const ctx = document.getElementById('monthlyChart').getContext('2d');
        
        // Extract data for chart
        const months = data.monthly_data.map(item => item.month_name);
        const incomeData = data.monthly_data.map(item => item.income);
        const expenseData = data.monthly_data.map(item => item.expenses);
        const profitData = data.monthly_data.map(item => item.profit);
        
        // Destroy existing chart if it exists
        if (monthlyChart) {
            monthlyChart.destroy();
        }
        
        // Create new chart
        monthlyChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: months,
                datasets: [
                    {
                        label: 'Income',
                        data: incomeData,
                        backgroundColor: 'rgba(40, 167, 69, 0.7)',
                        borderColor: 'rgba(40, 167, 69, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Expenses',
                        data: expenseData,
                        backgroundColor: 'rgba(220, 53, 69, 0.7)',
                        borderColor: 'rgba(220, 53, 69, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Net Profit',
                        data: profitData,
                        type: 'line',
                        backgroundColor: 'rgba(23, 162, 184, 0.2)',
                        borderColor: 'rgba(23, 162, 184, 1)',
                        borderWidth: 2,
                        pointBackgroundColor: 'rgba(23, 162, 184, 1)',
                        pointRadius: 4,
                        fill: false,
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString();
                            }
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += 'TZS ' + context.raw.toLocaleString();
                                return label;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Edit transaction
    function editTransaction(id) {
        fetch(`/api/finance/transactions/${id}`)
            .then(response => response.json())
            .then(transaction => {
                // Fill form with transaction data
                transactionId.value = transaction.id;
                transactionDate.value = transaction.date.substring(0, 10);
                transactionDescription.value = transaction.description;
                transactionAmount.value = transaction.amount;
                transactionType.value = transaction.transaction_type;
                transactionCategory.value = transaction.category;
                transactionPaymentMethod.value = transaction.payment_method || '';
                transactionReference.value = transaction.reference_id || '';
                transactionNotes.value = transaction.notes || '';
                
                // Update modal title and show delete button
                transactionModalLabel.textContent = 'Edit Transaction';
                deleteTransactionBtn.style.display = 'block';
                
                // Show modal
                transactionModal.show();
            })
            .catch(error => {
                console.error('Error loading transaction:', error);
                alert('Error loading transaction details. Please try again.');
            });
    }
    
    // Save transaction (create or update)
    function saveTransaction() {
        // Validate form
        if (!transactionForm.checkValidity()) {
            transactionForm.reportValidity();
            return;
        }
        
        // Build transaction data
        const transactionData = {
            date: transactionDate.value,
            description: transactionDescription.value,
            amount: parseFloat(transactionAmount.value),
            transaction_type: transactionType.value,
            category: transactionCategory.value,
            payment_method: transactionPaymentMethod.value || null,
            reference_id: transactionReference.value || null,
            notes: transactionNotes.value || null
        };
        
        // Determine if this is an update or a new transaction
        const isUpdate = transactionId.value !== '';
        
        // Set up request options
        const url = isUpdate 
            ? `/api/finance/transactions/${transactionId.value}`
            : '/api/finance/transactions';
        
        const method = isUpdate ? 'PUT' : 'POST';
        
        // Send request
        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(transactionData)
        })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.error || 'Error saving transaction'); });
                }
                return response.json();
            })
            .then(() => {
                // Close modal and reload data
                transactionModal.hide();
                loadTransactions();
                loadMonthlySummary();
                
                // Show success message
                alert(isUpdate ? 'Transaction updated successfully!' : 'Transaction added successfully!');
            })
            .catch(error => {
                console.error('Error saving transaction:', error);
                alert(error.message || 'Error saving transaction. Please try again.');
            });
    }
    
    // Delete transaction
    function deleteTransaction(id) {
        fetch(`/api/finance/transactions/${id}`, {
            method: 'DELETE'
        })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.error || 'Error deleting transaction'); });
                }
                return response.json();
            })
            .then(() => {
                // Close modals and reload data
                deleteConfirmModal.hide();
                transactionModal.hide();
                loadTransactions();
                loadMonthlySummary();
                
                // Show success message
                alert('Transaction deleted successfully!');
            })
            .catch(error => {
                console.error('Error deleting transaction:', error);
                alert(error.message || 'Error deleting transaction. Please try again.');
                deleteConfirmModal.hide();
            });
    }
    
    // Reset transaction form
    function resetTransactionForm() {
        transactionForm.reset();
        transactionId.value = '';
    }
    
    // Populate year select for monthly chart
    function populateYearSelect() {
        const currentYear = new Date().getFullYear();
        yearSelect.innerHTML = '';
        
        // Add 5 years past and 2 years future
        for (let year = currentYear - 5; year <= currentYear + 2; year++) {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            
            if (year === currentYear) {
                option.selected = true;
            }
            
            yearSelect.appendChild(option);
        }
    }
    
    // Format date for display (YYYY-MM-DD -> DD/MM/YYYY)
    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-GB');
    }
    
    // Format date for input fields (Date -> YYYY-MM-DD)
    function formatDateForInput(date) {
        return date.toISOString().substring(0, 10);
    }
});