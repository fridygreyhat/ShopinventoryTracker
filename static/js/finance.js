
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    const filterBtn = document.getElementById('filter-btn');
    
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
    const grossProfitValue = document.getElementById('gross-profit-value');
    const profitValue = document.getElementById('profit-value');
    
    // Chart instances
    let monthlyCashFlowChart = null;
    let accumulatedCashFlowChart = null;
    
    // Set default dates (current month)
    const today = new Date();
    const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    
    // Format dates for input fields
    startDateInput.value = formatDateForInput(firstDayOfMonth);
    endDateInput.value = formatDateForInput(today);
    
    // Set default dates for other sections
    const plStartDate = document.getElementById('pl-start-date');
    const plEndDate = document.getElementById('pl-end-date');
    const balanceSheetDate = document.getElementById('balance-sheet-date');
    const trialBalanceDate = document.getElementById('trial-balance-date');
    
    if (plStartDate) plStartDate.value = formatDateForInput(firstDayOfMonth);
    if (plEndDate) plEndDate.value = formatDateForInput(today);
    if (balanceSheetDate) balanceSheetDate.value = formatDateForInput(today);
    if (trialBalanceDate) trialBalanceDate.value = formatDateForInput(today);
    
    // Load initial data
    loadCategories();
    loadTransactions();
    loadCashFlow();
    loadProfitLoss();
    loadBalanceSheet();
    loadTrialBalance();
    loadChartOfAccounts();
    loadJournalEntries();
    loadBankAccounts();
    loadBankTransfers();
    loadBranchEquity();
    
    // Event listeners
    filterBtn.addEventListener('click', function() {
        loadTransactions();
        loadCashFlow();
    });
    
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
    
    document.getElementById('sync-accounting-btn').addEventListener('click', syncWithAccounting);
    
    // Accounting module event listeners
    document.getElementById('initializeAccountingBtn')?.addEventListener('click', initializeAccounting);
    document.getElementById('saveAccountBtn')?.addEventListener('click', saveAccount);
    document.getElementById('saveJournalEntryBtn')?.addEventListener('click', saveJournalEntry);
    document.getElementById('addJournalEntryRowBtn')?.addEventListener('click', addJournalEntryRow);
    document.getElementById('saveBankAccountBtn')?.addEventListener('click', saveBankAccount);
    document.getElementById('saveBankTransferBtn')?.addEventListener('click', saveBankTransfer);
    
    // Date change listeners for different sections
    plStartDate?.addEventListener('change', loadProfitLoss);
    plEndDate?.addEventListener('change', loadProfitLoss);
    balanceSheetDate?.addEventListener('change', loadBalanceSheet);
    trialBalanceDate?.addEventListener('change', loadTrialBalance);
    
    // Branch location filter
    document.getElementById('branch-location-filter')?.addEventListener('change', loadBranchEquity);
    
    // Journal entry calculations
    document.addEventListener('input', function(e) {
        if (e.target.classList.contains('debit-amount') || e.target.classList.contains('credit-amount')) {
            calculateJournalTotals();
        }
    });
    
    // Tab change listeners to load data when tabs are activated
    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(event) {
            const targetId = event.target.getAttribute('data-bs-target');
            
            // Update active state for vertical navigation
            document.querySelectorAll('.finance-nav-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            switch(targetId) {
                case '#cash-flow-content':
                    loadCashFlow();
                    break;
                case '#profit-loss-content':
                    loadProfitLoss();
                    break;
                case '#balance-sheet-content':
                    loadBalanceSheet();
                    break;
                case '#trial-balance-content':
                    loadTrialBalance();
                    break;
                case '#general-ledger-content':
                    loadGeneralLedger();
                    break;
                case '#chart-accounts-content':
                    loadChartOfAccounts();
                    break;
                case '#journal-content':
                    loadJournalEntries();
                    break;
                case '#bank-transfers-content':
                    loadBankAccounts();
                    loadBankTransfers();
                    break;
                case '#reconcile-content':
                    loadReconciliation();
                    break;
                case '#branch-equity-content':
                    loadBranchEquity();
                    break;
            }
        });
    });
    
    // Add click handlers for vertical navigation buttons
    document.querySelectorAll('.finance-nav-btn').forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            document.querySelectorAll('.finance-nav-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            // Add active class to clicked button
            this.classList.add('active');
        });
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
                showErrorInTables();
            });
    }
    
    // Load cash flow data
    function loadCashFlow() {
        const startDate = startDateInput.value;
        const endDate = endDateInput.value;
        
        let url = '/api/accounting/cash-flow';
        const params = [];
        
        if (startDate) params.push(`start_date=${startDate}`);
        if (endDate) params.push(`end_date=${endDate}`);
        
        if (params.length > 0) {
            url += '?' + params.join('&');
        }
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                displayCashFlow(data.cash_flows);
                createCashFlowCharts(data.monthly_summary);
            })
            .catch(error => {
                console.error('Error loading cash flow:', error);
                document.getElementById('cash-flow-table').innerHTML = 
                    '<tr><td colspan="6" class="text-center text-danger">Error loading cash flow data</td></tr>';
            });
    }
    
    // Load profit & loss statement
    function loadProfitLoss() {
        const startDate = plStartDate?.value || formatDateForInput(firstDayOfMonth);
        const endDate = plEndDate?.value || formatDateForInput(today);
        
        fetch(`/api/accounting/profit-loss?start_date=${startDate}&end_date=${endDate}`)
            .then(response => response.json())
            .then(data => {
                displayProfitLoss(data);
            })
            .catch(error => {
                console.error('Error loading profit & loss:', error);
            });
    }
    
    // Load balance sheet
    function loadBalanceSheet() {
        const asOfDate = balanceSheetDate?.value || formatDateForInput(today);
        
        fetch(`/api/accounting/balance-sheet?as_of_date=${asOfDate}`)
            .then(response => response.json())
            .then(data => {
                displayBalanceSheet(data);
            })
            .catch(error => {
                console.error('Error loading balance sheet:', error);
            });
    }
    
    // Load trial balance
    function loadTrialBalance() {
        const asOfDate = trialBalanceDate?.value || formatDateForInput(today);
        
        fetch(`/api/accounting/trial-balance?as_of_date=${asOfDate}`)
            .then(response => response.json())
            .then(data => {
                displayTrialBalance(data);
            })
            .catch(error => {
                console.error('Error loading trial balance:', error);
            });
    }
    
    // Load chart of accounts
    function loadChartOfAccounts() {
        fetch('/api/accounting/chart-of-accounts')
            .then(response => response.json())
            .then(data => {
                displayChartOfAccounts(data.accounts);
                populateAccountSelects(data.accounts);
            })
            .catch(error => {
                console.error('Error loading chart of accounts:', error);
            });
    }
    
    // Load journal entries
    function loadJournalEntries() {
        fetch('/api/accounting/journal-entries')
            .then(response => response.json())
            .then(data => {
                displayJournalEntries(data.journals);
            })
            .catch(error => {
                console.error('Error loading journal entries:', error);
            });
    }
    
    // Load general ledger
    function loadGeneralLedger() {
        const accountFilter = document.getElementById('ledger-account-filter')?.value || '';
        let url = '/api/accounting/general-ledger';
        
        if (accountFilter) {
            url += `?account_id=${accountFilter}`;
        }
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                displayGeneralLedger(data.entries);
            })
            .catch(error => {
                console.error('Error loading general ledger:', error);
            });
    }
    
    // Load bank accounts and transfers
    function loadBankAccounts() {
        fetch('/api/accounting/bank-accounts')
            .then(response => response.json())
            .then(data => {
                displayBankAccounts(data.accounts);
                populateBankAccountSelects(data.accounts);
            })
            .catch(error => {
                console.error('Error loading bank accounts:', error);
            });
    }
    
    function loadBankTransfers() {
        fetch('/api/accounting/bank-transfers')
            .then(response => response.json())
            .then(data => {
                displayBankTransfers(data.transfers);
            })
            .catch(error => {
                console.error('Error loading bank transfers:', error);
            });
    }
    
    // Load branch equity
    function loadBranchEquity() {
        const locationId = document.getElementById('branch-location-filter')?.value;
        
        if (!locationId) {
            document.getElementById('branch-equity-table').innerHTML = 
                '<tr><td colspan="6" class="text-center">Select a branch/location to view equity details</td></tr>';
            return;
        }
        
        fetch(`/api/accounting/branch-equity/${locationId}`)
            .then(response => response.json())
            .then(data => {
                displayBranchEquity(data.equity_records, data.location);
            })
            .catch(error => {
                console.error('Error loading branch equity:', error);
            });
    }
    
    // Load reconciliation data
    function loadReconciliation() {
        // Implementation for reconciliation
        console.log('Loading reconciliation data...');
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
    
    // Display functions
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
        displayTransactionsByType(incomeTransactions, incomeTransactionsTable, 'income');
        
        // Display expense transactions
        displayTransactionsByType(expenseTransactions, expenseTransactionsTable, 'expense');
        
        // Add event listeners to edit buttons
        document.querySelectorAll('.edit-transaction-btn').forEach(button => {
            button.addEventListener('click', function() {
                const id = this.getAttribute('data-id');
                editTransaction(id);
            });
        });
    }
    
    function displayTransactionsByType(transactions, tableElement, type) {
        if (transactions.length === 0) {
            tableElement.innerHTML = `<tr><td colspan="5" class="text-center">No ${type} transactions found for the selected period</td></tr>`;
        } else {
            let html = '';
            const colorClass = type === 'income' ? 'text-success' : 'text-danger';
            
            transactions.forEach(transaction => {
                html += `
                <tr>
                    <td>${formatDate(transaction.date)}</td>
                    <td>${transaction.description}</td>
                    <td>${transaction.category}</td>
                    <td class="${colorClass}">
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
            
            tableElement.innerHTML = html;
        }
    }
    
    function displayCashFlow(cashFlows) {
        const tableBody = document.getElementById('cash-flow-table');
        if (!tableBody) return;
        
        if (cashFlows.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center">No cash flow data found</td></tr>';
            return;
        }
        
        let html = '';
        cashFlows.forEach(flow => {
            const netClass = flow.net_cash_flow >= 0 ? 'text-success' : 'text-danger';
            html += `
                <tr>
                    <td>${formatDate(flow.date)}</td>
                    <td class="text-success">${formatCurrency(flow.cash_in)}</td>
                    <td class="text-danger">${formatCurrency(flow.cash_out)}</td>
                    <td class="${netClass}">${formatCurrency(flow.net_cash_flow)}</td>
                    <td>${formatCurrency(flow.accumulated_cash)}</td>
                    <td>${flow.source || '-'}</td>
                </tr>
            `;
        });
        
        tableBody.innerHTML = html;
    }
    
    function displayProfitLoss(data) {
        // Update revenue breakdown
        const revenueBreakdown = document.getElementById('revenue-breakdown');
        const expenseBreakdown = document.getElementById('expense-breakdown');
        const totalRevenueAmount = document.getElementById('total-revenue-amount');
        const totalExpenseAmount = document.getElementById('total-expense-amount');
        const grossProfitAmount = document.getElementById('gross-profit-amount');
        const netProfitAmount = document.getElementById('net-profit-amount');
        
        if (revenueBreakdown && data.revenue_breakdown) {
            let revenueHtml = '';
            Object.entries(data.revenue_breakdown).forEach(([category, amount]) => {
                revenueHtml += `
                    <div class="d-flex justify-content-between">
                        <span>${category}:</span>
                        <span>${formatCurrency(amount)}</span>
                    </div>
                `;
            });
            revenueBreakdown.innerHTML = revenueHtml;
        }
        
        if (expenseBreakdown && data.expense_breakdown) {
            let expenseHtml = '';
            Object.entries(data.expense_breakdown).forEach(([category, amount]) => {
                expenseHtml += `
                    <div class="d-flex justify-content-between">
                        <span>${category}:</span>
                        <span>${formatCurrency(amount)}</span>
                    </div>
                `;
            });
            expenseBreakdown.innerHTML = expenseHtml;
        }
        
        if (totalRevenueAmount) totalRevenueAmount.textContent = formatCurrency(data.total_revenue || 0);
        if (totalExpenseAmount) totalExpenseAmount.textContent = formatCurrency(data.total_expenses || 0);
        if (grossProfitAmount) grossProfitAmount.textContent = formatCurrency(data.gross_profit || 0);
        if (netProfitAmount) netProfitAmount.textContent = formatCurrency(data.net_profit || 0);
    }
    
    function displayBalanceSheet(data) {
        const assetsBreakdown = document.getElementById('assets-breakdown');
        const liabilitiesBreakdown = document.getElementById('liabilities-breakdown');
        const equityBreakdown = document.getElementById('equity-breakdown');
        const totalAssets = document.getElementById('balance-total-assets');
        const totalLiabilities = document.getElementById('balance-total-liabilities');
        const totalEquity = document.getElementById('balance-total-equity');
        const balanceCheckResult = document.getElementById('balance-check-result');
        
        if (assetsBreakdown && data.asset_breakdown) {
            let assetsHtml = '';
            Object.entries(data.asset_breakdown).forEach(([category, amount]) => {
                assetsHtml += `
                    <div class="d-flex justify-content-between">
                        <span>${category}:</span>
                        <span>${formatCurrency(amount)}</span>
                    </div>
                `;
            });
            assetsBreakdown.innerHTML = assetsHtml;
        }
        
        if (liabilitiesBreakdown && data.liability_breakdown) {
            let liabilitiesHtml = '';
            Object.entries(data.liability_breakdown).forEach(([category, amount]) => {
                liabilitiesHtml += `
                    <div class="d-flex justify-content-between">
                        <span>${category}:</span>
                        <span>${formatCurrency(amount)}</span>
                    </div>
                `;
            });
            liabilitiesBreakdown.innerHTML = liabilitiesHtml;
        }
        
        if (equityBreakdown && data.equity_breakdown) {
            let equityHtml = '';
            Object.entries(data.equity_breakdown).forEach(([category, amount]) => {
                equityHtml += `
                    <div class="d-flex justify-content-between">
                        <span>${category}:</span>
                        <span>${formatCurrency(amount)}</span>
                    </div>
                `;
            });
            equityBreakdown.innerHTML = equityHtml;
        }
        
        if (totalAssets) totalAssets.textContent = formatCurrency(data.total_assets || 0);
        if (totalLiabilities) totalLiabilities.textContent = formatCurrency(data.total_liabilities || 0);
        if (totalEquity) totalEquity.textContent = formatCurrency(data.total_equity || 0);
        
        if (balanceCheckResult) {
            balanceCheckResult.textContent = data.balance_check ? '✅ BALANCED' : '❌ NOT BALANCED';
            balanceCheckResult.className = data.balance_check ? 'text-success' : 'text-danger';
        }
    }
    
    function displayTrialBalance(data) {
        const tableBody = document.getElementById('trial-balance-table');
        const totalDebits = document.getElementById('trial-balance-total-debits');
        const totalCredits = document.getElementById('trial-balance-total-credits');
        
        if (!tableBody) return;
        
        if (!data.accounts || data.accounts.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center">No trial balance data found</td></tr>';
            return;
        }
        
        let html = '';
        data.accounts.forEach(account => {
            const typeClass = getAccountTypeClass(account.account_type);
            html += `
                <tr>
                    <td>${account.account_code}</td>
                    <td>${account.account_name}</td>
                    <td><span class="badge bg-${typeClass}">${account.account_type}</span></td>
                    <td class="text-end">${formatCurrency(account.debit_balance)}</td>
                    <td class="text-end">${formatCurrency(account.credit_balance)}</td>
                </tr>
            `;
        });
        
        tableBody.innerHTML = html;
        
        if (totalDebits) totalDebits.textContent = formatCurrency(data.total_debits || 0);
        if (totalCredits) totalCredits.textContent = formatCurrency(data.total_credits || 0);
    }
    
    function displayChartOfAccounts(accounts) {
        const tableBody = document.getElementById('chart-accounts-table');
        if (!tableBody) return;
        
        if (!accounts || accounts.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center">No accounts found. Initialize accounting to create default accounts.</td></tr>';
            return;
        }
        
        let html = '';
        accounts.forEach(account => {
            const typeClass = getAccountTypeClass(account.account_type);
            const statusBadge = account.is_active ? 
                '<span class="badge bg-success">Active</span>' : 
                '<span class="badge bg-secondary">Inactive</span>';
            
            html += `
                <tr>
                    <td>${account.account_code}</td>
                    <td>${account.account_name}</td>
                    <td><span class="badge bg-${typeClass}">${account.account_type}</span></td>
                    <td class="text-end">${formatCurrency(account.balance || 0)}</td>
                    <td>${statusBadge}</td>
                    <td>
                        <button class="btn btn-sm btn-primary edit-account-btn" data-id="${account.id}">
                            <i class="fas fa-edit"></i>
                        </button>
                    </td>
                </tr>
            `;
        });
        
        tableBody.innerHTML = html;
    }
    
    function displayJournalEntries(journals) {
        const tableBody = document.getElementById('journal-entries-table');
        if (!tableBody) return;
        
        if (!journals || journals.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center">No journal entries found</td></tr>';
            return;
        }
        
        let html = '';
        journals.forEach(journal => {
            html += `
                <tr>
                    <td>${journal.journal_number}</td>
                    <td>${formatDate(journal.date)}</td>
                    <td>${journal.description}</td>
                    <td class="text-end">${formatCurrency(journal.total_debit)}</td>
                    <td class="text-end">${formatCurrency(journal.total_credit)}</td>
                    <td>
                        <button class="btn btn-sm btn-primary view-journal-btn" data-id="${journal.id}">
                            <i class="fas fa-eye"></i>
                        </button>
                    </td>
                </tr>
            `;
        });
        
        tableBody.innerHTML = html;
    }
    
    function displayGeneralLedger(entries) {
        const tableBody = document.getElementById('general-ledger-table');
        if (!tableBody) return;
        
        if (!entries || entries.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="7" class="text-center">No ledger entries found</td></tr>';
            return;
        }
        
        let html = '';
        let runningBalance = 0;
        
        entries.forEach(entry => {
            runningBalance += (entry.debit_amount - entry.credit_amount);
            html += `
                <tr>
                    <td>${formatDate(entry.date)}</td>
                    <td>${entry.journal_number}</td>
                    <td>${entry.account_name}</td>
                    <td>${entry.description}</td>
                    <td class="text-end">${entry.debit_amount > 0 ? formatCurrency(entry.debit_amount) : ''}</td>
                    <td class="text-end">${entry.credit_amount > 0 ? formatCurrency(entry.credit_amount) : ''}</td>
                    <td class="text-end">${formatCurrency(runningBalance)}</td>
                </tr>
            `;
        });
        
        tableBody.innerHTML = html;
    }
    
    function displayBankAccounts(accounts) {
        const summaryDiv = document.getElementById('bank-accounts-summary');
        if (!summaryDiv) return;
        
        if (!accounts || accounts.length === 0) {
            summaryDiv.innerHTML = '<div class="text-center">No bank accounts found. Add a bank account to get started.</div>';
            return;
        }
        
        let html = '<div class="row">';
        accounts.forEach(account => {
            html += `
                <div class="col-md-4 mb-3">
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-title">${account.account_name}</h6>
                            <p class="card-text">
                                <small class="text-muted">${account.bank_name}</small><br>
                                <small class="text-muted">***${account.account_number.slice(-4)}</small>
                            </p>
                            <h5 class="text-primary">${formatCurrency(account.current_balance)}</h5>
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        
        summaryDiv.innerHTML = html;
    }
    
    function displayBankTransfers(transfers) {
        const tableBody = document.getElementById('bank-transfers-table');
        if (!tableBody) return;
        
        if (!transfers || transfers.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center">No transfers found</td></tr>';
            return;
        }
        
        let html = '';
        transfers.forEach(transfer => {
            const statusBadge = transfer.status === 'completed' ? 
                '<span class="badge bg-success">Completed</span>' : 
                '<span class="badge bg-warning">Pending</span>';
            
            html += `
                <tr>
                    <td>${transfer.transfer_number}</td>
                    <td>${transfer.from_account_name}</td>
                    <td>${transfer.to_account_name}</td>
                    <td class="text-end">${formatCurrency(transfer.amount)}</td>
                    <td>${formatDate(transfer.transfer_date)}</td>
                    <td>${statusBadge}</td>
                </tr>
            `;
        });
        
        tableBody.innerHTML = html;
    }
    
    function displayBranchEquity(equityRecords, location) {
        const tableBody = document.getElementById('branch-equity-table');
        const summaryDiv = document.getElementById('branch-equity-summary');
        
        if (!tableBody) return;
        
        if (!equityRecords || equityRecords.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center">No equity records found for this branch</td></tr>';
            return;
        }
        
        let html = '';
        equityRecords.forEach(record => {
            const roi = ((record.total_equity - record.capital_invested) / record.capital_invested * 100).toFixed(2);
            html += `
                <tr>
                    <td>${formatDate(record.date)}</td>
                    <td>${location?.name || 'Unknown'}</td>
                    <td class="text-end">${formatCurrency(record.capital_invested)}</td>
                    <td class="text-end">${formatCurrency(record.retained_earnings)}</td>
                    <td class="text-end">${formatCurrency(record.total_equity)}</td>
                    <td class="text-end ${roi >= 0 ? 'text-success' : 'text-danger'}">${roi}%</td>
                </tr>
            `;
        });
        
        tableBody.innerHTML = html;
        
        // Update summary
        if (summaryDiv && location) {
            const latestRecord = equityRecords[0];
            summaryDiv.innerHTML = `
                <div class="col-md-3">
                    <div class="card">
                        <div class="card-body text-center">
                            <h5>${location.name}</h5>
                            <p class="display-6 text-primary">${formatCurrency(latestRecord?.total_equity || 0)}</p>
                            <small class="text-muted">Total Equity</small>
                        </div>
                    </div>
                </div>
            `;
        }
    }
    
    // Create cash flow charts
    function createCashFlowCharts(monthlyData) {
        if (!monthlyData) return;
        
        // Monthly Cash Flow Chart
        const monthlyCtx = document.getElementById('monthlyCashFlowChart');
        if (monthlyCtx && monthlyCashFlowChart) {
            monthlyCashFlowChart.destroy();
        }
        
        if (monthlyCtx) {
            monthlyCashFlowChart = new Chart(monthlyCtx, {
                type: 'bar',
                data: {
                    labels: monthlyData.map(item => item.month),
                    datasets: [
                        {
                            label: 'Cash In',
                            data: monthlyData.map(item => item.cash_in),
                            backgroundColor: 'rgba(40, 167, 69, 0.7)',
                        },
                        {
                            label: 'Cash Out',
                            data: monthlyData.map(item => item.cash_out),
                            backgroundColor: 'rgba(220, 53, 69, 0.7)',
                        },
                        {
                            label: 'Net Flow',
                            data: monthlyData.map(item => item.net_flow),
                            type: 'line',
                            borderColor: 'rgba(23, 162, 184, 1)',
                            backgroundColor: 'rgba(23, 162, 184, 0.2)',
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
        
        // Accumulated Cash Flow Chart
        const accumulatedCtx = document.getElementById('accumulatedCashFlowChart');
        if (accumulatedCtx && accumulatedCashFlowChart) {
            accumulatedCashFlowChart.destroy();
        }
        
        if (accumulatedCtx) {
            accumulatedCashFlowChart = new Chart(accumulatedCtx, {
                type: 'line',
                data: {
                    labels: monthlyData.map(item => item.month),
                    datasets: [{
                        label: 'Accumulated Cash Flow',
                        data: monthlyData.map(item => item.net_flow),
                        borderColor: 'rgba(75, 192, 192, 1)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
    }
    
    // Update financial summary display
    function updateFinancialSummary(summary) {
        incomeValue.textContent = summary.total_income.toLocaleString();
        expensesValue.textContent = summary.total_expenses.toLocaleString();
        
        // Calculate gross profit (simplified as income - direct costs)
        const grossProfit = summary.total_income - (summary.cost_of_goods_sold || 0);
        grossProfitValue.textContent = grossProfit.toLocaleString();
        
        profitValue.textContent = summary.net_profit.toLocaleString();
        
        // Add color coding
        updateValueColor(grossProfitValue, grossProfit);
        updateValueColor(profitValue, summary.net_profit);
    }
    
    function updateValueColor(element, value) {
        element.classList.remove('text-success', 'text-danger');
        if (value > 0) {
            element.classList.add('text-success');
        } else if (value < 0) {
            element.classList.add('text-danger');
        }
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
                loadCashFlow();
                
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
                loadCashFlow();
                
                // Show success message
                alert('Transaction deleted successfully!');
            })
            .catch(error => {
                console.error('Error deleting transaction:', error);
                alert(error.message || 'Error deleting transaction. Please try again.');
                deleteConfirmModal.hide();
            });
    }
    
    // Accounting functions
    async function initializeAccounting() {
        try {
            const response = await fetch('/api/accounting/initialize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                alert('Chart of accounts initialized successfully!');
                loadChartOfAccounts();
            } else {
                const error = await response.json();
                alert('Error: ' + (error.error || 'Failed to initialize chart of accounts'));
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error initializing chart of accounts');
        }
    }
    
    async function saveAccount() {
        const form = document.getElementById('account-form');
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        const accountData = {
            account_code: document.getElementById('account-code').value,
            account_name: document.getElementById('account-name').value,
            account_type: document.getElementById('account-type').value,
            description: document.getElementById('account-description').value
        };
        
        try {
            const response = await fetch('/api/accounting/chart-of-accounts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(accountData)
            });
            
            if (response.ok) {
                const modal = bootstrap.Modal.getInstance(document.getElementById('addAccountModal'));
                modal.hide();
                form.reset();
                loadChartOfAccounts();
                alert('Account created successfully!');
            } else {
                const error = await response.json();
                alert('Error: ' + (error.error || 'Failed to create account'));
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error creating account');
        }
    }
    
    async function saveJournalEntry() {
        const entries = [];
        const rows = document.querySelectorAll('#journal-entries-body tr');
        
        rows.forEach(row => {
            const accountSelect = row.querySelector('.account-select');
            const description = row.querySelector('.entry-description');
            const debitAmount = row.querySelector('.debit-amount');
            const creditAmount = row.querySelector('.credit-amount');
            
            if (accountSelect.value) {
                entries.push({
                    account_id: parseInt(accountSelect.value),
                    description: description.value,
                    debit: parseFloat(debitAmount.value) || 0,
                    credit: parseFloat(creditAmount.value) || 0
                });
            }
        });
        
        if (entries.length < 2) {
            alert('Journal entry must have at least 2 entries');
            return;
        }
        
        const journalData = {
            description: document.getElementById('journal-description').value,
            reference_id: document.getElementById('journal-reference').value,
            entries: entries
        };
        
        try {
            const response = await fetch('/api/accounting/journal-entries', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(journalData)
            });
            
            if (response.ok) {
                const modal = bootstrap.Modal.getInstance(document.getElementById('journalEntryModal'));
                modal.hide();
                loadJournalEntries();
                alert('Journal entry created successfully!');
            } else {
                const error = await response.json();
                alert('Error: ' + (error.error || 'Failed to create journal entry'));
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error creating journal entry');
        }
    }
    
    function addJournalEntryRow() {
        const tbody = document.getElementById('journal-entries-body');
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <select class="form-select account-select" required>
                    <option value="">Select Account</option>
                </select>
            </td>
            <td>
                <input type="text" class="form-control entry-description">
            </td>
            <td>
                <input type="number" class="form-control debit-amount" step="0.01" min="0">
            </td>
            <td>
                <input type="number" class="form-control credit-amount" step="0.01" min="0">
            </td>
            <td>
                <button type="button" class="btn btn-danger btn-sm remove-entry">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        
        tbody.appendChild(row);
        
        // Populate account select for new row
        populateAccountSelect(row.querySelector('.account-select'));
        
        // Add remove event listener
        row.querySelector('.remove-entry').addEventListener('click', function() {
            row.remove();
            calculateJournalTotals();
        });
    }
    
    function calculateJournalTotals() {
        let totalDebits = 0;
        let totalCredits = 0;
        
        document.querySelectorAll('.debit-amount').forEach(input => {
            totalDebits += parseFloat(input.value) || 0;
        });
        
        document.querySelectorAll('.credit-amount').forEach(input => {
            totalCredits += parseFloat(input.value) || 0;
        });
        
        document.getElementById('total-debits').textContent = totalDebits.toFixed(2);
        document.getElementById('total-credits').textContent = totalCredits.toFixed(2);
    }
    
    async function saveBankAccount() {
        const form = document.getElementById('bank-account-form');
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        const accountData = {
            account_name: document.getElementById('bank-account-name').value,
            account_number: document.getElementById('bank-account-number').value,
            bank_name: document.getElementById('bank-name').value,
            account_type: document.getElementById('bank-account-type').value,
            current_balance: parseFloat(document.getElementById('initial-balance').value) || 0
        };
        
        try {
            const response = await fetch('/api/accounting/bank-accounts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(accountData)
            });
            
            if (response.ok) {
                const modal = bootstrap.Modal.getInstance(document.getElementById('addBankAccountModal'));
                modal.hide();
                form.reset();
                loadBankAccounts();
                alert('Bank account added successfully!');
            } else {
                const error = await response.json();
                alert('Error: ' + (error.error || 'Failed to add bank account'));
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error adding bank account');
        }
    }
    
    async function saveBankTransfer() {
        const form = document.getElementById('bank-transfer-form');
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        const transferData = {
            from_account_id: parseInt(document.getElementById('from-account').value),
            to_account_id: parseInt(document.getElementById('to-account').value),
            amount: parseFloat(document.getElementById('transfer-amount').value),
            transfer_fee: parseFloat(document.getElementById('transfer-fee').value) || 0,
            description: document.getElementById('transfer-description').value
        };
        
        try {
            const response = await fetch('/api/accounting/bank-transfers', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(transferData)
            });
            
            if (response.ok) {
                const modal = bootstrap.Modal.getInstance(document.getElementById('bankTransferModal'));
                modal.hide();
                form.reset();
                loadBankTransfers();
                loadBankAccounts();
                alert('Bank transfer completed successfully!');
            } else {
                const error = await response.json();
                alert('Error: ' + (error.error || 'Failed to complete transfer'));
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error completing transfer');
        }
    }
    
    // Helper functions
    function populateAccountSelects(accounts) {
        const selects = document.querySelectorAll('.account-select');
        selects.forEach(select => {
            populateAccountSelect(select, accounts);
        });
        
        // Also populate ledger filter
        const ledgerFilter = document.getElementById('ledger-account-filter');
        if (ledgerFilter && accounts) {
            ledgerFilter.innerHTML = '<option value="">All Accounts</option>';
            accounts.forEach(account => {
                const option = document.createElement('option');
                option.value = account.id;
                option.textContent = `${account.account_code} - ${account.account_name}`;
                ledgerFilter.appendChild(option);
            });
        }
    }
    
    function populateAccountSelect(selectElement, accounts = null) {
        if (!accounts) {
            // If accounts not provided, fetch them
            fetch('/api/accounting/chart-of-accounts')
                .then(response => response.json())
                .then(data => populateAccountSelect(selectElement, data.accounts))
                .catch(error => console.error('Error loading accounts:', error));
            return;
        }
        
        selectElement.innerHTML = '<option value="">Select Account</option>';
        accounts.forEach(account => {
            const option = document.createElement('option');
            option.value = account.id;
            option.textContent = `${account.account_code} - ${account.account_name}`;
            selectElement.appendChild(option);
        });
    }
    
    function populateBankAccountSelects(accounts) {
        const fromSelect = document.getElementById('from-account');
        const toSelect = document.getElementById('to-account');
        
        [fromSelect, toSelect].forEach(select => {
            if (select) {
                select.innerHTML = '<option value="">Select Account</option>';
                accounts.forEach(account => {
                    const option = document.createElement('option');
                    option.value = account.id;
                    option.textContent = `${account.account_name} (${account.bank_name})`;
                    select.appendChild(option);
                });
            }
        });
    }
    
    function getAccountTypeClass(type) {
        const colors = {
            'Asset': 'success',
            'Liability': 'warning',
            'Equity': 'info',
            'Revenue': 'primary',
            'Expense': 'danger'
        };
        return colors[type] || 'secondary';
    }
    
    function resetTransactionForm() {
        transactionForm.reset();
        transactionId.value = '';
    }
    
    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-GB');
    }
    
    function formatDateForInput(date) {
        return date.toISOString().substring(0, 10);
    }
    
    function formatCurrency(amount) {
        return `TZS ${parseFloat(amount || 0).toLocaleString()}`;
    }
    
    function showErrorInTables() {
        allTransactionsTable.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Error loading transactions</td></tr>';
        incomeTransactionsTable.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error loading income transactions</td></tr>';
        expenseTransactionsTable.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error loading expense transactions</td></tr>';
    }
    
    // Sync financial data with accounting
    async function syncWithAccounting() {
        const syncBtn = document.getElementById('sync-accounting-btn');
        const originalText = syncBtn.innerHTML;
        
        syncBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Syncing...';
        syncBtn.disabled = true;
        
        try {
            const response = await fetch('/api/finance/sync-accounting', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (response.ok) {
                alert(`Sync completed! ${result.message}`);
                loadTransactions();
                loadCashFlow();
                loadProfitLoss();
                loadBalanceSheet();
                loadTrialBalance();
            } else {
                alert('Sync failed: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Sync error:', error);
            alert('Sync failed: Network error');
        } finally {
            syncBtn.innerHTML = originalText;
            syncBtn.disabled = false;
        }
    }
});
