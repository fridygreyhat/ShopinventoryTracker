
document.addEventListener('DOMContentLoaded', function() {
    // Initialize page
    loadQuickStats();
    loadChartOfAccounts();
    loadJournalEntries();
    
    // Set default dates
    const today = new Date().toISOString().split('T')[0];
    const firstOfMonth = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0];
    
    document.getElementById('trial-balance-date').value = today;
    document.getElementById('balance-sheet-date').value = today;
    document.getElementById('income-start-date').value = firstOfMonth;
    document.getElementById('income-end-date').value = today;
    document.getElementById('cashflow-start-date').value = firstOfMonth;
    document.getElementById('cashflow-end-date').value = today;
    document.getElementById('je-date').value = today;
    document.getElementById('recon-date').value = today;
    
    // Event listeners
    document.getElementById('initialize-accounting-btn').addEventListener('click', initializeAccounting);
    document.getElementById('save-account-btn').addEventListener('click', saveAccount);
    document.getElementById('load-trial-balance-btn').addEventListener('click', loadTrialBalance);
    document.getElementById('load-income-statement-btn').addEventListener('click', loadIncomeStatement);
    document.getElementById('load-balance-sheet-btn').addEventListener('click', loadBalanceSheet);
    document.getElementById('load-cash-flow-btn').addEventListener('click', loadCashFlowStatement);
    document.getElementById('load-general-ledger-btn').addEventListener('click', loadGeneralLedger);
    document.getElementById('add-journal-entry-row').addEventListener('click', addJournalEntryRow);
    document.getElementById('save-journal-entry-btn').addEventListener('click', saveJournalEntry);
    document.getElementById('save-reconciliation-btn').addEventListener('click', saveReconciliation);
    
    // Date change listeners for journal entries
    document.getElementById('journal-start-date').addEventListener('change', loadJournalEntries);
    document.getElementById('journal-end-date').addEventListener('change', loadJournalEntries);
    
    // Tab change listeners
    document.querySelector('[data-bs-target="#reconciliation"]').addEventListener('click', loadReconciliations);
    
    function initializeAccounting() {
        if (confirm('This will create the standard chart of accounts. Continue?')) {
            fetch('/api/accounting/initialize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Chart of accounts initialized successfully!');
                    loadChartOfAccounts();
                    loadQuickStats();
                } else {
                    alert('Error: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error initializing accounting system');
            });
        }
    }
    
    function loadQuickStats() {
        // Load balance sheet data for quick stats
        fetch('/api/accounting/balance-sheet')
            .then(response => response.json())
            .then(data => {
                document.getElementById('total-assets').textContent = 'TZS ' + data.assets.total.toLocaleString();
                document.getElementById('total-liabilities').textContent = 'TZS ' + data.liabilities.total.toLocaleString();
                document.getElementById('total-equity').textContent = 'TZS ' + data.equity.total.toLocaleString();
            })
            .catch(error => console.error('Error loading quick stats:', error));
        
        // Load trial balance status
        fetch('/api/accounting/trial-balance')
            .then(response => response.json())
            .then(data => {
                const statusElement = document.getElementById('trial-balance-status');
                if (data.is_balanced) {
                    statusElement.className = 'badge bg-success';
                    statusElement.textContent = 'Balanced';
                } else {
                    statusElement.className = 'badge bg-danger';
                    statusElement.textContent = 'Out of Balance';
                }
            })
            .catch(error => console.error('Error loading trial balance status:', error));
    }
    
    function loadChartOfAccounts() {
        fetch('/api/accounting/chart-of-accounts')
            .then(response => response.json())
            .then(accounts => {
                const tableBody = document.getElementById('chart-of-accounts-table');
                
                if (accounts.length === 0) {
                    tableBody.innerHTML = '<tr><td colspan="6" class="text-center">No accounts found. Click "Initialize Chart of Accounts" to get started.</td></tr>';
                    return;
                }
                
                tableBody.innerHTML = accounts.map(account => `
                    <tr>
                        <td>${account.code}</td>
                        <td>${account.name}</td>
                        <td>
                            <span class="badge bg-${getAccountTypeBadgeColor(account.account_type)}">
                                ${account.account_type}
                            </span>
                        </td>
                        <td>${account.normal_balance}</td>
                        <td class="text-end">TZS ${account.current_balance.toLocaleString()}</td>
                        <td>
                            <button class="btn btn-sm btn-primary" onclick="editAccount(${account.id})">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-sm btn-info" onclick="viewGeneralLedger(${account.id})">
                                <i class="fas fa-book"></i>
                            </button>
                        </td>
                    </tr>
                `).join('');
                
                // Populate account selects
                populateAccountSelects(accounts);
            })
            .catch(error => {
                console.error('Error loading chart of accounts:', error);
                document.getElementById('chart-of-accounts-table').innerHTML = 
                    '<tr><td colspan="6" class="text-center text-danger">Error loading accounts</td></tr>';
            });
    }
    
    function populateAccountSelects(accounts) {
        const selects = [
            'ledger-account-select',
            'recon-bank-account'
        ];
        
        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            if (select) {
                select.innerHTML = '<option value="">Select Account</option>';
                accounts.forEach(account => {
                    if (selectId === 'recon-bank-account' && !account.code.startsWith('10')) {
                        return; // Only show cash/bank accounts for reconciliation
                    }
                    select.innerHTML += `<option value="${account.id}">${account.code} - ${account.name}</option>`;
                });
            }
        });
    }
    
    function getAccountTypeBadgeColor(type) {
        const colors = {
            'Asset': 'primary',
            'Liability': 'danger',
            'Equity': 'info',
            'Income': 'success',
            'Expense': 'warning'
        };
        return colors[type] || 'secondary';
    }
    
    function saveAccount() {
        const accountData = {
            code: document.getElementById('account-code').value,
            name: document.getElementById('account-name').value,
            account_type: document.getElementById('account-type').value,
            normal_balance: document.getElementById('normal-balance').value,
            description: document.getElementById('account-description').value
        };
        
        fetch('/api/accounting/accounts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(accountData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error: ' + data.error);
            } else {
                bootstrap.Modal.getInstance(document.getElementById('accountModal')).hide();
                loadChartOfAccounts();
                document.getElementById('account-form').reset();
                alert('Account created successfully!');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error creating account');
        });
    }
    
    function loadJournalEntries() {
        const startDate = document.getElementById('journal-start-date').value;
        const endDate = document.getElementById('journal-end-date').value;
        
        let url = '/api/accounting/journal-entries';
        const params = [];
        
        if (startDate) params.push(`start_date=${startDate}`);
        if (endDate) params.push(`end_date=${endDate}`);
        
        if (params.length > 0) {
            url += '?' + params.join('&');
        }
        
        fetch(url)
            .then(response => response.json())
            .then(entries => {
                const tableBody = document.getElementById('journal-entries-table');
                
                if (entries.length === 0) {
                    tableBody.innerHTML = '<tr><td colspan="7" class="text-center">No journal entries found</td></tr>';
                    return;
                }
                
                // Group entries by transaction group
                const groupedEntries = {};
                entries.forEach(entry => {
                    if (!groupedEntries[entry.transaction_group]) {
                        groupedEntries[entry.transaction_group] = [];
                    }
                    groupedEntries[entry.transaction_group].push(entry);
                });
                
                let html = '';
                Object.keys(groupedEntries).forEach(group => {
                    const groupEntries = groupedEntries[group];
                    groupEntries.forEach((entry, index) => {
                        html += `
                            <tr ${index === 0 ? 'class="border-top border-3"' : ''}>
                                <td>${index === 0 ? entry.entry_number : ''}</td>
                                <td>${index === 0 ? formatDate(entry.date) : ''}</td>
                                <td>${entry.account_code} - ${entry.account_name}</td>
                                <td>${entry.description}</td>
                                <td class="text-end">${entry.debit_amount > 0 ? 'TZS ' + entry.debit_amount.toLocaleString() : ''}</td>
                                <td class="text-end">${entry.credit_amount > 0 ? 'TZS ' + entry.credit_amount.toLocaleString() : ''}</td>
                                <td>
                                    <span class="badge bg-${getEntryTypeBadgeColor(entry.reference_type)}">
                                        ${entry.reference_type || 'manual'}
                                    </span>
                                </td>
                            </tr>
                        `;
                    });
                });
                
                tableBody.innerHTML = html;
            })
            .catch(error => {
                console.error('Error loading journal entries:', error);
                document.getElementById('journal-entries-table').innerHTML = 
                    '<tr><td colspan="7" class="text-center text-danger">Error loading journal entries</td></tr>';
            });
    }
    
    function getEntryTypeBadgeColor(type) {
        const colors = {
            'sale': 'success',
            'purchase': 'primary',
            'expense': 'warning',
            'manual': 'info'
        };
        return colors[type] || 'secondary';
    }
    
    function loadTrialBalance() {
        const asOfDate = document.getElementById('trial-balance-date').value;
        let url = '/api/accounting/trial-balance';
        
        if (asOfDate) {
            url += '?as_of_date=' + asOfDate;
        }
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                const tableBody = document.getElementById('trial-balance-table');
                
                if (data.trial_balance.length === 0) {
                    tableBody.innerHTML = '<tr><td colspan="4" class="text-center">No data found</td></tr>';
                    return;
                }
                
                tableBody.innerHTML = data.trial_balance.map(item => `
                    <tr>
                        <td>${item.account_code}</td>
                        <td>${item.account_name}</td>
                        <td class="text-end">${item.debit_balance > 0 ? 'TZS ' + item.debit_balance.toLocaleString() : ''}</td>
                        <td class="text-end">${item.credit_balance > 0 ? 'TZS ' + item.credit_balance.toLocaleString() : ''}</td>
                    </tr>
                `).join('');
                
                // Update totals
                document.getElementById('total-debits').textContent = 'TZS ' + data.total_debits.toLocaleString();
                document.getElementById('total-credits').textContent = 'TZS ' + data.total_credits.toLocaleString();
                
                // Update status
                const statusElement = document.getElementById('trial-balance-status');
                if (data.is_balanced) {
                    statusElement.className = 'badge bg-success';
                    statusElement.textContent = 'Balanced';
                } else {
                    statusElement.className = 'badge bg-danger';
                    statusElement.textContent = 'Out of Balance';
                }
            })
            .catch(error => {
                console.error('Error loading trial balance:', error);
                document.getElementById('trial-balance-table').innerHTML = 
                    '<tr><td colspan="4" class="text-center text-danger">Error loading trial balance</td></tr>';
            });
    }
    
    function loadIncomeStatement() {
        const startDate = document.getElementById('income-start-date').value;
        const endDate = document.getElementById('income-end-date').value;
        
        let url = '/api/accounting/income-statement';
        const params = [];
        
        if (startDate) params.push(`start_date=${startDate}`);
        if (endDate) params.push(`end_date=${endDate}`);
        
        if (params.length > 0) {
            url += '?' + params.join('&');
        }
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                const content = document.getElementById('income-statement-content');
                
                let html = `
                    <div class="row">
                        <div class="col-12">
                            <h6 class="text-center">Profit & Loss Statement</h6>
                            <p class="text-center text-muted">
                                ${formatDate(data.period.start_date)} to ${formatDate(data.period.end_date)}
                            </p>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <h6>Revenue</h6>
                            <table class="table table-sm">
                `;
                
                data.revenue.items.forEach(item => {
                    html += `
                        <tr>
                            <td>${item.account_name}</td>
                            <td class="text-end">TZS ${item.amount.toLocaleString()}</td>
                        </tr>
                    `;
                });
                
                html += `
                        <tr class="fw-bold border-top">
                            <td>Total Revenue</td>
                            <td class="text-end">TZS ${data.revenue.total.toLocaleString()}</td>
                        </tr>
                    </table>
                    
                    <h6>Expenses</h6>
                    <table class="table table-sm">
                `;
                
                data.expenses.items.forEach(item => {
                    html += `
                        <tr>
                            <td>${item.account_name}</td>
                            <td class="text-end">TZS ${item.amount.toLocaleString()}</td>
                        </tr>
                    `;
                });
                
                html += `
                        <tr class="fw-bold border-top">
                            <td>Total Expenses</td>
                            <td class="text-end">TZS ${data.expenses.total.toLocaleString()}</td>
                        </tr>
                    </table>
                        </div>
                        
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-body text-center">
                                    <h6>Net Income</h6>
                                    <h3 class="${data.net_income >= 0 ? 'text-success' : 'text-danger'}">
                                        TZS ${data.net_income.toLocaleString()}
                                    </h3>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                content.innerHTML = html;
            })
            .catch(error => {
                console.error('Error loading income statement:', error);
                document.getElementById('income-statement-content').innerHTML = 
                    '<p class="text-center text-danger">Error loading income statement</p>';
            });
    }
    
    function loadBalanceSheet() {
        const asOfDate = document.getElementById('balance-sheet-date').value;
        let url = '/api/accounting/balance-sheet';
        
        if (asOfDate) {
            url += '?as_of_date=' + asOfDate;
        }
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                const content = document.getElementById('balance-sheet-content');
                
                let html = `
                    <div class="row">
                        <div class="col-12">
                            <h6 class="text-center">Balance Sheet</h6>
                            <p class="text-center text-muted">As of ${formatDate(data.as_of_date)}</p>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <h6>Assets</h6>
                            <table class="table table-sm">
                `;
                
                data.assets.items.forEach(item => {
                    html += `
                        <tr>
                            <td>${item.account_name}</td>
                            <td class="text-end">TZS ${item.amount.toLocaleString()}</td>
                        </tr>
                    `;
                });
                
                html += `
                        <tr class="fw-bold border-top">
                            <td>Total Assets</td>
                            <td class="text-end">TZS ${data.assets.total.toLocaleString()}</td>
                        </tr>
                    </table>
                        </div>
                        
                        <div class="col-md-6">
                            <h6>Liabilities</h6>
                            <table class="table table-sm">
                `;
                
                data.liabilities.items.forEach(item => {
                    html += `
                        <tr>
                            <td>${item.account_name}</td>
                            <td class="text-end">TZS ${item.amount.toLocaleString()}</td>
                        </tr>
                    `;
                });
                
                html += `
                        <tr class="fw-bold border-top">
                            <td>Total Liabilities</td>
                            <td class="text-end">TZS ${data.liabilities.total.toLocaleString()}</td>
                        </tr>
                    </table>
                    
                    <h6>Equity</h6>
                    <table class="table table-sm">
                `;
                
                data.equity.items.forEach(item => {
                    html += `
                        <tr>
                            <td>${item.account_name}</td>
                            <td class="text-end">TZS ${item.amount.toLocaleString()}</td>
                        </tr>
                    `;
                });
                
                html += `
                        <tr class="fw-bold border-top">
                            <td>Total Equity</td>
                            <td class="text-end">TZS ${data.equity.total.toLocaleString()}</td>
                        </tr>
                        <tr class="fw-bold border-top">
                            <td>Total Liabilities & Equity</td>
                            <td class="text-end">TZS ${data.total_liabilities_and_equity.toLocaleString()}</td>
                        </tr>
                    </table>
                        </div>
                    </div>
                `;
                
                content.innerHTML = html;
            })
            .catch(error => {
                console.error('Error loading balance sheet:', error);
                document.getElementById('balance-sheet-content').innerHTML = 
                    '<p class="text-center text-danger">Error loading balance sheet</p>';
            });
    }
    
    function loadCashFlowStatement() {
        const startDate = document.getElementById('cashflow-start-date').value;
        const endDate = document.getElementById('cashflow-end-date').value;
        
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
                const content = document.getElementById('cash-flow-content');
                
                let html = `
                    <div class="row">
                        <div class="col-12">
                            <h6 class="text-center">Cash Flow Statement</h6>
                            <p class="text-center text-muted">
                                ${formatDate(data.period.start_date)} to ${formatDate(data.period.end_date)}
                            </p>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-4">
                            <h6>Operating Activities</h6>
                            <table class="table table-sm">
                `;
                
                data.operating_activities.items.forEach(item => {
                    html += `
                        <tr>
                            <td>${item.description}</td>
                            <td class="text-end">TZS ${item.amount.toLocaleString()}</td>
                        </tr>
                    `;
                });
                
                html += `
                        <tr class="fw-bold border-top">
                            <td>Net Operating Cash Flow</td>
                            <td class="text-end">TZS ${data.operating_activities.total.toLocaleString()}</td>
                        </tr>
                    </table>
                        </div>
                        
                        <div class="col-md-4">
                            <h6>Investing Activities</h6>
                            <table class="table table-sm">
                `;
                
                data.investing_activities.items.forEach(item => {
                    html += `
                        <tr>
                            <td>${item.description}</td>
                            <td class="text-end">TZS ${item.amount.toLocaleString()}</td>
                        </tr>
                    `;
                });
                
                html += `
                        <tr class="fw-bold border-top">
                            <td>Net Investing Cash Flow</td>
                            <td class="text-end">TZS ${data.investing_activities.total.toLocaleString()}</td>
                        </tr>
                    </table>
                        </div>
                        
                        <div class="col-md-4">
                            <h6>Financing Activities</h6>
                            <table class="table table-sm">
                `;
                
                data.financing_activities.items.forEach(item => {
                    html += `
                        <tr>
                            <td>${item.description}</td>
                            <td class="text-end">TZS ${item.amount.toLocaleString()}</td>
                        </tr>
                    `;
                });
                
                html += `
                        <tr class="fw-bold border-top">
                            <td>Net Financing Cash Flow</td>
                            <td class="text-end">TZS ${data.financing_activities.total.toLocaleString()}</td>
                        </tr>
                    </table>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-12">
                            <div class="card">
                                <div class="card-body text-center">
                                    <h6>Net Change in Cash</h6>
                                    <h4 class="${data.net_change_in_cash >= 0 ? 'text-success' : 'text-danger'}">
                                        TZS ${data.net_change_in_cash.toLocaleString()}
                                    </h4>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                content.innerHTML = html;
            })
            .catch(error => {
                console.error('Error loading cash flow statement:', error);
                document.getElementById('cash-flow-content').innerHTML = 
                    '<p class="text-center text-danger">Error loading cash flow statement</p>';
            });
    }
    
    function loadGeneralLedger() {
        const accountId = document.getElementById('ledger-account-select').value;
        const startDate = document.getElementById('ledger-start-date').value;
        const endDate = document.getElementById('ledger-end-date').value;
        
        if (!accountId) {
            alert('Please select an account');
            return;
        }
        
        let url = `/api/accounting/general-ledger/${accountId}`;
        const params = [];
        
        if (startDate) params.push(`start_date=${startDate}`);
        if (endDate) params.push(`end_date=${endDate}`);
        
        if (params.length > 0) {
            url += '?' + params.join('&');
        }
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                const content = document.getElementById('general-ledger-content');
                
                let html = `
                    <h6>${data.account.code} - ${data.account.name}</h6>
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Description</th>
                                <th>Debit</th>
                                <th>Credit</th>
                                <th>Balance</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                data.entries.forEach(entry => {
                    html += `
                        <tr>
                            <td>${formatDate(entry.date)}</td>
                            <td>${entry.description}</td>
                            <td class="text-end">${entry.debit_amount > 0 ? 'TZS ' + entry.debit_amount.toLocaleString() : ''}</td>
                            <td class="text-end">${entry.credit_amount > 0 ? 'TZS ' + entry.credit_amount.toLocaleString() : ''}</td>
                            <td class="text-end">TZS ${entry.running_balance.toLocaleString()}</td>
                        </tr>
                    `;
                });
                
                html += `
                        </tbody>
                        <tfoot>
                            <tr class="fw-bold">
                                <td colspan="4">Ending Balance</td>
                                <td class="text-end">TZS ${data.ending_balance.toLocaleString()}</td>
                            </tr>
                        </tfoot>
                    </table>
                `;
                
                content.innerHTML = html;
            })
            .catch(error => {
                console.error('Error loading general ledger:', error);
                document.getElementById('general-ledger-content').innerHTML = 
                    '<p class="text-center text-danger">Error loading general ledger</p>';
            });
    }
    
    function loadReconciliations() {
        fetch('/api/accounting/reconciliation')
            .then(response => response.json())
            .then(reconciliations => {
                const tableBody = document.getElementById('reconciliation-table');
                
                if (reconciliations.length === 0) {
                    tableBody.innerHTML = '<tr><td colspan="7" class="text-center">No reconciliation records found</td></tr>';
                    return;
                }
                
                tableBody.innerHTML = reconciliations.map(recon => `
                    <tr>
                        <td>${formatDate(recon.reconciliation_date)}</td>
                        <td>${recon.bank_account_name}</td>
                        <td class="text-end">TZS ${recon.bank_statement_balance.toLocaleString()}</td>
                        <td class="text-end">TZS ${recon.book_balance.toLocaleString()}</td>
                        <td class="text-end">TZS ${recon.reconciled_balance.toLocaleString()}</td>
                        <td>
                            <span class="badge bg-${recon.is_reconciled ? 'success' : 'warning'}">
                                ${recon.is_reconciled ? 'Reconciled' : 'Pending'}
                            </span>
                        </td>
                        <td>
                            <button class="btn btn-sm btn-primary" onclick="editReconciliation(${recon.id})">
                                <i class="fas fa-edit"></i>
                            </button>
                        </td>
                    </tr>
                `).join('');
            })
            .catch(error => {
                console.error('Error loading reconciliations:', error);
                document.getElementById('reconciliation-table').innerHTML = 
                    '<tr><td colspan="7" class="text-center text-danger">Error loading reconciliation records</td></tr>';
            });
    }
    
    function addJournalEntryRow() {
        const container = document.getElementById('journal-entries-container');
        const rowIndex = container.children.length;
        
        const row = document.createElement('div');
        row.className = 'row mb-2 journal-entry-row';
        row.innerHTML = `
            <div class="col-md-4">
                <select class="form-select account-select" required>
                    <option value="">Select Account</option>
                </select>
            </div>
            <div class="col-md-3">
                <input type="text" class="form-control description-input" placeholder="Description" required>
            </div>
            <div class="col-md-2">
                <input type="number" step="0.01" class="form-control debit-input" placeholder="Debit" min="0">
            </div>
            <div class="col-md-2">
                <input type="number" step="0.01" class="form-control credit-input" placeholder="Credit" min="0">
            </div>
            <div class="col-md-1">
                <button type="button" class="btn btn-sm btn-danger" onclick="removeJournalEntryRow(this)">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        
        container.appendChild(row);
        
        // Populate account dropdown
        populateJournalAccountSelect(row.querySelector('.account-select'));
        
        // Add event listeners for calculation
        row.querySelector('.debit-input').addEventListener('input', calculateJournalTotals);
        row.querySelector('.credit-input').addEventListener('input', calculateJournalTotals);
        
        // Ensure only debit or credit is filled
        row.querySelector('.debit-input').addEventListener('input', function() {
            if (this.value) {
                row.querySelector('.credit-input').value = '';
            }
        });
        
        row.querySelector('.credit-input').addEventListener('input', function() {
            if (this.value) {
                row.querySelector('.debit-input').value = '';
            }
        });
    }
    
    function removeJournalEntryRow(button) {
        button.closest('.journal-entry-row').remove();
        calculateJournalTotals();
    }
    
    function populateJournalAccountSelect(select) {
        fetch('/api/accounting/chart-of-accounts')
            .then(response => response.json())
            .then(accounts => {
                accounts.forEach(account => {
                    const option = document.createElement('option');
                    option.value = account.id;
                    option.textContent = `${account.code} - ${account.name}`;
                    select.appendChild(option);
                });
            })
            .catch(error => console.error('Error loading accounts for journal entry:', error));
    }
    
    function calculateJournalTotals() {
        const debitInputs = document.querySelectorAll('.debit-input');
        const creditInputs = document.querySelectorAll('.credit-input');
        
        let totalDebits = 0;
        let totalCredits = 0;
        
        debitInputs.forEach(input => {
            if (input.value) {
                totalDebits += parseFloat(input.value);
            }
        });
        
        creditInputs.forEach(input => {
            if (input.value) {
                totalCredits += parseFloat(input.value);
            }
        });
        
        document.getElementById('total-debits-amount').textContent = totalDebits.toFixed(2);
        document.getElementById('total-credits-amount').textContent = totalCredits.toFixed(2);
        
        // Enable/disable save button based on balance
        const saveButton = document.getElementById('save-journal-entry-btn');
        const isBalanced = Math.abs(totalDebits - totalCredits) < 0.01 && totalDebits > 0;
        saveButton.disabled = !isBalanced;
        
        if (isBalanced) {
            saveButton.className = 'btn btn-primary';
        } else {
            saveButton.className = 'btn btn-secondary';
        }
    }
    
    function saveJournalEntry() {
        const rows = document.querySelectorAll('.journal-entry-row');
        const entries = [];
        
        rows.forEach(row => {
            const accountId = row.querySelector('.account-select').value;
            const description = row.querySelector('.description-input').value;
            const debitAmount = row.querySelector('.debit-input').value;
            const creditAmount = row.querySelector('.credit-input').value;
            
            if (accountId && description && (debitAmount || creditAmount)) {
                entries.push({
                    account_id: parseInt(accountId),
                    description: description,
                    debit_amount: parseFloat(debitAmount) || 0,
                    credit_amount: parseFloat(creditAmount) || 0
                });
            }
        });
        
        if (entries.length < 2) {
            alert('At least two journal entries are required for double-entry bookkeeping');
            return;
        }
        
        const journalData = {
            date: document.getElementById('je-date').value,
            entries: entries
        };
        
        fetch('/api/accounting/journal-entries', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(journalData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error: ' + data.error);
            } else {
                bootstrap.Modal.getInstance(document.getElementById('journalEntryModal')).hide();
                loadJournalEntries();
                loadQuickStats();
                
                // Clear form
                document.getElementById('journal-entries-container').innerHTML = '';
                addJournalEntryRow();
                addJournalEntryRow();
                
                alert('Journal entry created successfully!');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error creating journal entry');
        });
    }
    
    function saveReconciliation() {
        const reconData = {
            bank_account_id: document.getElementById('recon-bank-account').value,
            reconciliation_date: document.getElementById('recon-date').value,
            bank_statement_balance: parseFloat(document.getElementById('recon-bank-balance').value),
            book_balance: parseFloat(document.getElementById('recon-book-balance').value),
            outstanding_deposits: parseFloat(document.getElementById('recon-deposits').value) || 0,
            outstanding_checks: parseFloat(document.getElementById('recon-checks').value) || 0,
            bank_fees: parseFloat(document.getElementById('recon-fees').value) || 0,
            notes: document.getElementById('recon-notes').value
        };
        
        // Calculate reconciled balance
        reconData.reconciled_balance = reconData.book_balance + reconData.outstanding_deposits - reconData.outstanding_checks - reconData.bank_fees;
        reconData.is_reconciled = Math.abs(reconData.reconciled_balance - reconData.bank_statement_balance) < 0.01;
        
        fetch('/api/accounting/reconciliation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(reconData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error: ' + data.error);
            } else {
                bootstrap.Modal.getInstance(document.getElementById('reconciliationModal')).hide();
                loadReconciliations();
                document.getElementById('reconciliation-form').reset();
                alert('Bank reconciliation saved successfully!');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error saving bank reconciliation');
        });
    }
    
    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-GB');
    }
    
    // Initialize journal entry form with two rows
    addJournalEntryRow();
    addJournalEntryRow();
    
    // Global functions for buttons
    window.editAccount = function(accountId) {
        // Implementation for editing accounts
        console.log('Edit account:', accountId);
    };
    
    window.viewGeneralLedger = function(accountId) {
        // Switch to general ledger tab and load account
        document.querySelector('[data-bs-target="#general-ledger"]').click();
        document.getElementById('ledger-account-select').value = accountId;
        setTimeout(() => loadGeneralLedger(), 100);
    };
    
    window.editReconciliation = function(reconId) {
        // Implementation for editing reconciliation
        console.log('Edit reconciliation:', reconId);
    };
    
    window.removeJournalEntryRow = removeJournalEntryRow;
});
