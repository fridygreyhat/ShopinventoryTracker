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
        const categorySelect = document.getElementById('transaction-category');

        // Enhanced categories with more options
        const defaultCategories = {
            income: [
                'Sales Revenue',
                'Service Income', 
                'Interest Income',
                'Investment Income',
                'Rental Income',
                'Commission Income',
                'Consulting Income',
                'Freelance Income',
                'Royalty Income',
                'Other Income'
            ],
            expense: [
                'Rent & Utilities',
                'Office Supplies',
                'Marketing & Advertising',
                'Transportation',
                'Equipment & Machinery',
                'Professional Services',
                'Insurance',
                'Telecommunications',
                'Training & Development',
                'Travel & Accommodation',
                'Maintenance & Repairs',
                'Bank Charges',
                'Taxes & Licenses',
                'Raw Materials',
                'Employee Salaries',
                'Other Expenses'
            ]
        };

        // Clear existing options
        categorySelect.innerHTML = '<option value="">Select Category</option>';

        // Add income categories
        const incomeGroup = document.createElement('optgroup');
        incomeGroup.label = 'Income Categories';
        defaultCategories.income.forEach(category => {
            const option = document.createElement('option');
            option.value = category;
            option.textContent = category;
            option.setAttribute('data-type', 'Income');
            incomeGroup.appendChild(option);
        });
        categorySelect.appendChild(incomeGroup);

        // Add expense categories
        const expenseGroup = document.createElement('optgroup');
        expenseGroup.label = 'Expense Categories';
        defaultCategories.expense.forEach(category => {
            const option = document.createElement('option');
            option.value = category;
            option.textContent = category;
            option.setAttribute('data-type', 'Expense');
            expenseGroup.appendChild(option);
        });
        categorySelect.appendChild(expenseGroup);

        // Load and add saved custom categories
        const savedCategories = JSON.parse(localStorage.getItem('customCategories') || '[]');
        if (savedCategories.length > 0) {
            const customGroup = document.createElement('optgroup');
            customGroup.label = 'Custom Categories';
            savedCategories.forEach(category => {
                const option = document.createElement('option');
                option.value = category.name;
                option.textContent = category.name;
                option.setAttribute('data-type', category.type);
                customGroup.appendChild(option);
            });
            categorySelect.appendChild(customGroup);
        }

        // Handle category selection
        categorySelect.addEventListener('change', function() {
            const customCategoryInput = document.getElementById('custom-category-input');
            const selectedValue = this.value;
            
            // Remove existing custom input
            if (customCategoryInput) {
                customCategoryInput.remove();
            }
            
            // Check if "Other" category is selected
            if (selectedValue === 'Other Income' || selectedValue === 'Other Expenses') {
                createCustomCategoryInput(selectedValue);
            } else {
                // Auto-select transaction type based on category
                const selectedOption = this.options[this.selectedIndex];
                const categoryType = selectedOption.getAttribute('data-type');
                if (categoryType) {
                    document.getElementById('transaction-type').value = categoryType;
                }
            }
        });
    }

    // Create custom category input
    function createCustomCategoryInput(selectedCategory = null) {
        const categoryGroup = document.getElementById('transaction-category').closest('.form-group');
        const customDiv = document.createElement('div');
        customDiv.id = 'custom-category-input';
        customDiv.className = 'mt-2';
        
        // Determine the type based on selected category
        let categoryType = '';
        let placeholder = 'Specify the category';
        
        if (selectedCategory === 'Other Income') {
            categoryType = 'Income';
            placeholder = 'Specify the income category (e.g., Grants, Donations, etc.)';
        } else if (selectedCategory === 'Other Expenses') {
            categoryType = 'Expense';
            placeholder = 'Specify the expense category (e.g., Miscellaneous, Legal Fees, etc.)';
        }
        
        customDiv.innerHTML = `
            <div class="mb-2">
                <label class="form-label small text-muted">Specify Category Details:</label>
            </div>
            <div class="row">
                <div class="col-md-12">
                    <input type="text" class="form-control" id="custom-category-name" 
                           placeholder="${placeholder}" 
                           data-category-type="${categoryType}">
                </div>
            </div>
            <div class="mt-2">
                <button type="button" class="btn btn-sm btn-success" onclick="saveCustomCategory()">
                    <i class="fas fa-check"></i> Save Category
                </button>
                <button type="button" class="btn btn-sm btn-secondary" onclick="cancelCustomCategory()">
                    Cancel
                </button>
            </div>
        `;
        categoryGroup.appendChild(customDiv);
        
        // Auto-select the transaction type
        if (categoryType) {
            document.getElementById('transaction-type').value = categoryType;
        }
        
        // Focus on the input field
        setTimeout(() => {
            document.getElementById('custom-category-name').focus();
        }, 100);
    }

    // Save custom category
    window.saveCustomCategory = function() {
        const categoryNameInput = document.getElementById('custom-category-name');
        const categoryName = categoryNameInput.value.trim();
        const categoryType = categoryNameInput.getAttribute('data-category-type');

        if (!categoryName) {
            alert('Please enter a category name');
            categoryNameInput.focus();
            return;
        }

        if (!categoryType) {
            alert('Category type not specified');
            return;
        }

        const categorySelect = document.getElementById('transaction-category');

        // Find or create the custom categories group
        let customGroup = categorySelect.querySelector('optgroup[label="Custom Categories"]');
        if (!customGroup) {
            customGroup = document.createElement('optgroup');
            customGroup.label = 'Custom Categories';
            categorySelect.appendChild(customGroup);
        }

        // Add new option to the custom group
        const newOption = document.createElement('option');
        newOption.value = categoryName;
        newOption.textContent = categoryName;
        newOption.setAttribute('data-type', categoryType);
        customGroup.appendChild(newOption);

        // Select the new category
        categorySelect.value = categoryName;
        document.getElementById('transaction-type').value = categoryType;

        // Remove custom input
        document.getElementById('custom-category-input').remove();

        // Save custom category to localStorage for persistence
        const savedCategories = JSON.parse(localStorage.getItem('customCategories') || '[]');
        
        // Check if category already exists
        const existingCategory = savedCategories.find(cat => cat.name === categoryName && cat.type === categoryType);
        if (!existingCategory) {
            savedCategories.push({ name: categoryName, type: categoryType });
            localStorage.setItem('customCategories', JSON.stringify(savedCategories));
        }

        // Show success message
        const successMsg = document.createElement('div');
        successMsg.className = 'alert alert-success alert-dismissible fade show mt-2';
        successMsg.innerHTML = `
            <i class="fas fa-check-circle"></i> Custom category "${categoryName}" saved successfully!
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        categorySelect.closest('.form-group').appendChild(successMsg);

        // Auto-dismiss after 3 seconds
        setTimeout(() => {
            if (successMsg.parentNode) {
                successMsg.remove();
            }
        }, 3000);
    };

    // Cancel custom category
    window.cancelCustomCategory = function() {
        document.getElementById('transaction-category').value = '';
        document.getElementById('custom-category-input').remove();
    };

    // Update financial summary
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

    // Display transactions in tables
    function displayTransactions(transactions) {
        // Clear existing table content
        allTransactionsTable.innerHTML = '';
        incomeTransactionsTable.innerHTML = '';
        expenseTransactionsTable.innerHTML = '';

        if (transactions.length === 0) {
            allTransactionsTable.innerHTML = '<tr><td colspan="6" class="text-center">No transactions found</td></tr>';
            incomeTransactionsTable.innerHTML = '<tr><td colspan="5" class="text-center">No income transactions found</td></tr>';
            expenseTransactionsTable.innerHTML = '<tr><td colspan="5" class="text-center">No expense transactions found</td></tr>';
            return;
        }

        // Filter transactions
        const incomeTransactions = transactions.filter(t => t.transaction_type === 'Income');
        const expenseTransactions = transactions.filter(t => t.transaction_type === 'Expense');

        // Display all transactions
        transactions.forEach(transaction => {
            const row = createTransactionRow(transaction, true);
            allTransactionsTable.appendChild(row);
        });

        // Display income transactions
        if (incomeTransactions.length === 0) {
            incomeTransactionsTable.innerHTML = '<tr><td colspan="5" class="text-center">No income transactions found</td></tr>';
        } else {
            incomeTransactions.forEach(transaction => {
                const row = createTransactionRow(transaction, false);
                incomeTransactionsTable.appendChild(row);
            });
        }

        // Display expense transactions
        if (expenseTransactions.length === 0) {
            expenseTransactionsTable.innerHTML = '<tr><td colspan="5" class="text-center">No expense transactions found</td></tr>';
        } else {
            expenseTransactions.forEach(transaction => {
                const row = createTransactionRow(transaction, false);
                expenseTransactionsTable.appendChild(row);
            });
        }
    }

    // Create transaction row
    function createTransactionRow(transaction, showType) {
        const row = document.createElement('tr');
        
        const typeClass = transaction.transaction_type === 'Income' ? 'text-success' : 'text-danger';
        const typeIcon = transaction.transaction_type === 'Income' ? 'fas fa-arrow-up' : 'fas fa-arrow-down';
        
        const cols = showType ? 6 : 5;
        
        row.innerHTML = `
            <td>${formatDate(transaction.date)}</td>
            <td>
                <div class="fw-bold">${transaction.description}</div>
                ${transaction.reference_id ? `<small class="text-muted">Ref: ${transaction.reference_id}</small>` : ''}
            </td>
            <td>
                <span class="badge bg-light text-dark">${transaction.category}</span>
            </td>
            <td class="${typeClass}">
                <i class="${typeIcon}"></i> TZS ${transaction.amount.toLocaleString()}
            </td>
            ${showType ? `<td><span class="badge ${transaction.transaction_type === 'Income' ? 'bg-success' : 'bg-danger'}">${transaction.transaction_type}</span></td>` : ''}
            <td>
                <div class="btn-group" role="group">
                    <button type="button" class="btn btn-sm btn-outline-primary" onclick="editTransaction(${transaction.id})" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-danger" onclick="deleteTransactionConfirm(${transaction.id})" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        `;
        
        return row;
    }

    // Delete transaction with confirmation
    window.deleteTransactionConfirm = function(id) {
        transactionId.value = id;
        deleteConfirmModal.show();
    };

    // Create monthly chart
    function createMonthlyChart(data) {
        const ctx = document.getElementById('monthlyChart').getContext('2d');

        // Extract data for chart
        const months = data.monthly_data.map(item => item.month_name);
        const incomeData = data.monthly_data.map(item => item.income);
        const expenseData = data.monthly_data.map(item => item.expenses);
        const profitData = data.monthly_data.map(item => item.profit);

        // Destroy existing chart if it exists
        if (window.monthlyChart) {
            window.monthlyChart.destroy();
        }

        // Create new chart
        window.monthlyChart = new Chart(ctx, {
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