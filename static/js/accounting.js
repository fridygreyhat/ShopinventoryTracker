
document.addEventListener('DOMContentLoaded', function() {
    // Chart instances
    let cashFlowChart = null;
    
    // Initialize accounting module
    initializeAccounting();
    
    function initializeAccounting() {
        loadChartOfAccounts();
        loadJournalEntries();
        loadTrialBalance();
        loadProfitLoss();
        loadBalanceSheet();
        loadCashFlow();
        loadBankAccounts();
        loadBankTransfers();
        updateDashboardCards();
        
        // Set up event listeners
        setupEventListeners();
    }
    
    function setupEventListeners() {
        // Initialize accounting button
        document.getElementById('initializeAccountingBtn')?.addEventListener('click', initializeChartOfAccounts);
        
        // Add account button
        document.getElementById('saveAccountBtn')?.addEventListener('click', saveAccount);
        
        // Add journal entry button
        document.getElementById('saveJournalEntryBtn')?.addEventListener('click', saveJournalEntry);
        document.getElementById('addJournalEntryRowBtn')?.addEventListener('click', addJournalEntryRow);
        
        // Bank account and transfer buttons
        document.getElementById('saveBankAccountBtn')?.addEventListener('click', saveBankAccount);
        document.getElementById('saveBankTransferBtn')?.addEventListener('click', saveBankTransfer);
        
        // Date change listeners
        document.getElementById('trial-balance-date')?.addEventListener('change', loadTrialBalance);
        document.getElementById('balance-sheet-date')?.addEventListener('change', loadBalanceSheet);
        document.getElementById('pl-start-date')?.addEventListener('change', loadProfitLoss);
        document.getElementById('pl-end-date')?.addEventListener('change', loadProfitLoss);
        
        // Journal entry calculations
        document.addEventListener('input', function(e) {
            if (e.target.classList.contains('debit-amount') || e.target.classList.contains('credit-amount')) {
                calculateJournalTotals();
            }
        });
    }
    
    async function initializeChartOfAccounts() {
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
    
    async function loadChartOfAccounts() {
        try {
            const response = await fetch('/api/accounting/chart-of-accounts');
            const data = await response.json();
            
            if (data.accounts) {
                displayChartOfAccounts(data.accounts);
                populateAccountSelects(data.accounts);
            }
        } catch (error) {
            console.error('Error loading chart of accounts:', error);
        }
    }
    
    function displayChartOfAccounts(accounts) {
        const tableBody = document.getElementById('chart-accounts-table');
        if (!tableBody) return;
        
        if (accounts.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center">No accounts found. Click "Initialize Accounting" to set up default accounts.</td></tr>';
            return;
        }
        
        let html = '';
        accounts.forEach(account => {
            html += `
                <tr>
                    <td>${account.account_code}</td>
                    <td>${account.account_name}</td>
                    <td><span class="badge bg-${getAccountTypeBadgeColor(account.account_type)}">${account.account_type}</span></td>
                    <td>${account.description || ''}</td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="editAccount(${account.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                    </td>
                </tr>
            `;
        });
        
        tableBody.innerHTML = html;
    }
    
    function getAccountTypeBadgeColor(type) {
        const colors = {
            'Asset': 'success',
            'Liability': 'warning',
            'Equity': 'info',
            'Revenue': 'primary',
            'Expense': 'danger'
        };
        return colors[type] || 'secondary';
    }
    
    function populateAccountSelects(accounts) {
        const selects = document.querySelectorAll('.account-select');
        selects.forEach(select => {
            select.innerHTML = '<option value="">Select Account</option>';
            accounts.forEach(account => {
                const option = document.createElement('option');
                option.value = account.id;
                option.textContent = `${account.account_code} - ${account.account_name}`;
                select.appendChild(option);
            });
        });
        
        // Populate bank account selects
        populateBankAccountSelects();
    }
    
    async function loadJournalEntries() {
        try {
            const response = await fetch('/api/accounting/journal-entries');
            const data = await response.json();
            
            if (data.journals) {
                displayJournalEntries(data.journals);
            }
        } catch (error) {
            console.error('Error loading journal entries:', error);
        }
    }
    
    function displayJournalEntries(journals) {
        const tableBody = document.getElementById('journal-entries-table');
        if (!tableBody) return;
        
        if (journals.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="7" class="text-center">No journal entries found</td></tr>';
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
                    <td><span class="badge bg-${journal.status === 'posted' ? 'success' : 'warning'}">${journal.status}</span></td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="viewJournalEntry(${journal.id})">
                            <i class="fas fa-eye"></i>
                        </button>
                    </td>
                </tr>
            `;
        });
        
        tableBody.innerHTML = html;
    }
    
    async function loadTrialBalance() {
        try {
            const dateInput = document.getElementById('trial-balance-date');
            const asOfDate = dateInput?.value || new Date().toISOString().split('T')[0];
            
            const response = await fetch(`/api/accounting/trial-balance?as_of_date=${asOfDate}`);
            const data = await response.json();
            
            displayTrialBalance(data);
        } catch (error) {
            console.error('Error loading trial balance:', error);
        }
    }
    
    function displayTrialBalance(data) {
        const tableBody = document.getElementById('trial-balance-table');
        const totalsFooter = document.getElementById('trial-balance-totals');
        
        if (!tableBody) return;
        
        if (!data.accounts || data.accounts.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center">No accounts found</td></tr>';
            if (totalsFooter) totalsFooter.style.display = 'none';
            return;
        }
        
        let html = '';
        data.accounts.forEach(account => {
            html += `
                <tr>
                    <td>${account.account_code}</td>
                    <td>${account.account_name}</td>
                    <td><span class="badge bg-${getAccountTypeBadgeColor(account.account_type)}">${account.account_type}</span></td>
                    <td class="text-end">${account.debit_balance > 0 ? formatCurrency(account.debit_balance) : ''}</td>
                    <td class="text-end">${account.credit_balance > 0 ? formatCurrency(account.credit_balance) : ''}</td>
                </tr>
            `;
        });
        
        tableBody.innerHTML = html;
        
        // Update totals
        if (totalsFooter) {
            totalsFooter.style.display = 'table-footer-group';
            document.getElementById('total-debits').textContent = formatCurrency(data.total_debits || 0);
            document.getElementById('total-credits').textContent = formatCurrency(data.total_credits || 0);
        }
    }
    
    async function loadProfitLoss() {
        try {
            const startDate = document.getElementById('pl-start-date')?.value;
            const endDate = document.getElementById('pl-end-date')?.value;
            
            let url = '/api/accounting/profit-loss';
            const params = [];
            
            if (startDate) params.push(`start_date=${startDate}`);
            if (endDate) params.push(`end_date=${endDate}`);
            
            if (params.length > 0) {
                url += '?' + params.join('&');
            }
            
            const response = await fetch(url);
            const data = await response.json();
            
            displayProfitLoss(data);
        } catch (error) {
            console.error('Error loading profit & loss:', error);
        }
    }
    
    function displayProfitLoss(data) {
        // Update revenue breakdown
        const revenueDiv = document.getElementById('revenue-breakdown');
        const expenseDiv = document.getElementById('expense-breakdown');
        
        if (revenueDiv && data.revenue_breakdown) {
            let revenueHtml = '';
            Object.entries(data.revenue_breakdown).forEach(([account, amount]) => {
                if (amount > 0) {
                    revenueHtml += `
                        <div class="d-flex justify-content-between">
                            <span>${account}</span>
                            <span>${formatCurrency(amount)}</span>
                        </div>
                    `;
                }
            });
            revenueDiv.innerHTML = revenueHtml || '<div class="text-muted">No revenue recorded</div>';
        }
        
        if (expenseDiv && data.expense_breakdown) {
            let expenseHtml = '';
            Object.entries(data.expense_breakdown).forEach(([account, amount]) => {
                if (amount > 0) {
                    expenseHtml += `
                        <div class="d-flex justify-content-between">
                            <span>${account}</span>
                            <span>${formatCurrency(amount)}</span>
                        </div>
                    `;
                }
            });
            expenseDiv.innerHTML = expenseHtml || '<div class="text-muted">No expenses recorded</div>';
        }
        
        // Update totals
        document.getElementById('total-revenue-amount').textContent = formatCurrency(data.total_revenue || 0);
        document.getElementById('total-expense-amount').textContent = formatCurrency(data.total_expenses || 0);
        document.getElementById('gross-profit-amount').textContent = formatCurrency(data.gross_profit || 0);
        document.getElementById('net-profit-amount').textContent = formatCurrency(data.net_profit || 0);
    }
    
    async function loadBalanceSheet() {
        try {
            const dateInput = document.getElementById('balance-sheet-date');
            const asOfDate = dateInput?.value || new Date().toISOString().split('T')[0];
            
            const response = await fetch(`/api/accounting/balance-sheet?as_of_date=${asOfDate}`);
            const data = await response.json();
            
            displayBalanceSheet(data);
        } catch (error) {
            console.error('Error loading balance sheet:', error);
        }
    }
    
    function displayBalanceSheet(data) {
        // Update assets
        const assetsDiv = document.getElementById('assets-breakdown');
        if (assetsDiv && data.asset_breakdown) {
            let assetsHtml = '';
            Object.entries(data.asset_breakdown).forEach(([account, amount]) => {
                if (amount !== 0) {
                    assetsHtml += `
                        <div class="d-flex justify-content-between">
                            <span>${account}</span>
                            <span>${formatCurrency(Math.abs(amount))}</span>
                        </div>
                    `;
                }
            });
            assetsDiv.innerHTML = assetsHtml || '<div class="text-muted">No assets recorded</div>';
        }
        
        // Update liabilities
        const liabilitiesDiv = document.getElementById('liabilities-breakdown');
        if (liabilitiesDiv && data.liability_breakdown) {
            let liabilitiesHtml = '';
            Object.entries(data.liability_breakdown).forEach(([account, amount]) => {
                if (amount !== 0) {
                    liabilitiesHtml += `
                        <div class="d-flex justify-content-between">
                            <span>${account}</span>
                            <span>${formatCurrency(Math.abs(amount))}</span>
                        </div>
                    `;
                }
            });
            liabilitiesDiv.innerHTML = liabilitiesHtml || '<div class="text-muted">No liabilities recorded</div>';
        }
        
        // Update equity
        const equityDiv = document.getElementById('equity-breakdown');
        if (equityDiv && data.equity_breakdown) {
            let equityHtml = '';
            Object.entries(data.equity_breakdown).forEach(([account, amount]) => {
                if (amount !== 0) {
                    equityHtml += `
                        <div class="d-flex justify-content-between">
                            <span>${account}</span>
                            <span>${formatCurrency(Math.abs(amount))}</span>
                        </div>
                    `;
                }
            });
            equityDiv.innerHTML = equityHtml || '<div class="text-muted">No equity recorded</div>';
        }
        
        // Update totals
        document.getElementById('balance-total-assets').textContent = formatCurrency(Math.abs(data.total_assets || 0));
        document.getElementById('balance-total-liabilities').textContent = formatCurrency(Math.abs(data.total_liabilities || 0));
        document.getElementById('balance-total-equity').textContent = formatCurrency(Math.abs(data.total_equity || 0));
        
        // Balance check
        const balanceCheck = document.getElementById('balance-check-result');
        if (balanceCheck) {
            const isBalanced = data.balance_check;
            balanceCheck.textContent = isBalanced ? '✅ BALANCED' : '❌ NOT BALANCED';
            balanceCheck.className = isBalanced ? 'text-success' : 'text-danger';
        }
    }
    
    async function loadCashFlow() {
        try {
            const response = await fetch('/api/accounting/cash-flow');
            const data = await response.json();
            
            displayCashFlow(data);
        } catch (error) {
            console.error('Error loading cash flow:', error);
        }
    }
    
    function displayCashFlow(data) {
        // Update cash flow table
        const tableBody = document.getElementById('cash-flow-table');
        if (!tableBody) return;
        
        if (!data.cash_flows || data.cash_flows.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center">No cash flow data found</td></tr>';
            return;
        }
        
        let html = '';
        data.cash_flows.forEach(cf => {
            html += `
                <tr>
                    <td>${formatDate(cf.date)}</td>
                    <td class="text-success text-end">${formatCurrency(cf.cash_in)}</td>
                    <td class="text-danger text-end">${formatCurrency(cf.cash_out)}</td>
                    <td class="text-end ${cf.net_cash_flow >= 0 ? 'text-success' : 'text-danger'}">${formatCurrency(cf.net_cash_flow)}</td>
                    <td class="text-end">${formatCurrency(cf.accumulated_cash)}</td>
                    <td>${cf.source || ''}</td>
                </tr>
            `;
        });
        
        tableBody.innerHTML = html;
        
        // Create cash flow chart
        if (data.monthly_summary) {
            createCashFlowChart(data.monthly_summary);
        }
    }
    
    function createCashFlowChart(monthlyData) {
        const ctx = document.getElementById('cashFlowChart');
        if (!ctx) return;
        
        if (cashFlowChart) {
            cashFlowChart.destroy();
        }
        
        const labels = monthlyData.map(item => item.month);
        const cashInData = monthlyData.map(item => item.cash_in);
        const cashOutData = monthlyData.map(item => item.cash_out);
        const netFlowData = monthlyData.map(item => item.net_flow);
        
        cashFlowChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Cash In',
                        data: cashInData,
                        borderColor: 'rgba(40, 167, 69, 1)',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        tension: 0.1
                    },
                    {
                        label: 'Cash Out',
                        data: cashOutData,
                        borderColor: 'rgba(220, 53, 69, 1)',
                        backgroundColor: 'rgba(220, 53, 69, 0.1)',
                        tension: 0.1
                    },
                    {
                        label: 'Net Flow',
                        data: netFlowData,
                        borderColor: 'rgba(23, 162, 184, 1)',
                        backgroundColor: 'rgba(23, 162, 184, 0.1)',
                        tension: 0.1
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
    
    async function loadBankAccounts() {
        try {
            const response = await fetch('/api/accounting/bank-accounts');
            const data = await response.json();
            
            displayBankAccounts(data.accounts || []);
        } catch (error) {
            console.error('Error loading bank accounts:', error);
        }
    }
    
    function displayBankAccounts(accounts) {
        const container = document.getElementById('bank-accounts-list');
        if (!container) return;
        
        if (accounts.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">No bank accounts found</div>';
            return;
        }
        
        let html = '';
        accounts.forEach(account => {
            html += `
                <div class="card mb-2">
                    <div class="card-body py-2">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <strong>${account.account_name}</strong><br>
                                <small class="text-muted">${account.bank_name} - ${account.account_number}</small>
                            </div>
                            <div class="text-end">
                                <div class="h6 mb-0">${formatCurrency(account.current_balance)}</div>
                                <small class="text-muted">${account.currency}</small>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    }
    
    async function loadBankTransfers() {
        try {
            const response = await fetch('/api/accounting/bank-transfers');
            const data = await response.json();
            
            displayBankTransfers(data.transfers || []);
        } catch (error) {
            console.error('Error loading bank transfers:', error);
        }
    }
    
    function displayBankTransfers(transfers) {
        const tableBody = document.getElementById('bank-transfers-table');
        if (!tableBody) return;
        
        if (transfers.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center">No transfers found</td></tr>';
            return;
        }
        
        let html = '';
        transfers.forEach(transfer => {
            html += `
                <tr>
                    <td>${transfer.transfer_number}</td>
                    <td>${transfer.from_account_name}</td>
                    <td>${transfer.to_account_name}</td>
                    <td class="text-end">${formatCurrency(transfer.amount)}</td>
                    <td>${formatDate(transfer.transfer_date)}</td>
                </tr>
            `;
        });
        
        tableBody.innerHTML = html;
    }
    
    async function updateDashboardCards() {
        try {
            // Load financial summary for dashboard cards
            const response = await fetch('/api/finance/transactions');
            const data = await response.json();
            
            if (data.summary) {
                const totalAssets = data.summary.total_income || 0;
                const totalLiabilities = data.summary.total_expenses * 0.3 || 0; // Estimate
                const totalEquity = totalAssets - totalLiabilities;
                const netCashFlow = data.summary.net_profit || 0;
                
                document.getElementById('total-assets').querySelector('span:last-child').textContent = totalAssets.toLocaleString();
                document.getElementById('total-liabilities').querySelector('span:last-child').textContent = totalLiabilities.toLocaleString();
                document.getElementById('total-equity').querySelector('span:last-child').textContent = totalEquity.toLocaleString();
                document.getElementById('net-cash-flow').querySelector('span:last-child').textContent = netCashFlow.toLocaleString();
            }
        } catch (error) {
            console.error('Error updating dashboard cards:', error);
        }
    }
    
    function populateBankAccountSelects() {
        fetch('/api/accounting/bank-accounts')
            .then(response => response.json())
            .then(data => {
                const fromSelect = document.getElementById('fromAccount');
                const toSelect = document.getElementById('toAccount');
                
                if (fromSelect && toSelect && data.accounts) {
                    const options = data.accounts.map(account => 
                        `<option value="${account.id}">${account.account_name} - ${account.bank_name}</option>`
                    ).join('');
                    
                    fromSelect.innerHTML = '<option value="">Select Account</option>' + options;
                    toSelect.innerHTML = '<option value="">Select Account</option>' + options;
                }
            });
    }
    
    // Event handlers
    async function saveAccount() {
        const form = document.getElementById('accountForm');
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        const accountData = {
            account_code: document.getElementById('accountCode').value,
            account_name: document.getElementById('accountName').value,
            account_type: document.getElementById('accountType').value,
            description: document.getElementById('accountDescription').value
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
                bootstrap.Modal.getInstance(document.getElementById('accountModal')).hide();
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
    
    function addJournalEntryRow() {
        const container = document.getElementById('journalEntriesContainer');
        const rowCount = container.children.length;
        
        const newRow = document.createElement('div');
        newRow.className = 'row journal-entry-row mb-2';
        newRow.innerHTML = `
            <div class="col-md-5">
                <select class="form-select account-select" required>
                    <option value="">Select Account</option>
                </select>
            </div>
            <div class="col-md-3">
                <input type="number" class="form-control debit-amount" placeholder="Debit" step="0.01" min="0">
            </div>
            <div class="col-md-3">
                <input type="number" class="form-control credit-amount" placeholder="Credit" step="0.01" min="0">
            </div>
            <div class="col-md-1">
                <button type="button" class="btn btn-sm btn-danger remove-entry-btn">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        
        container.appendChild(newRow);
        
        // Populate account select
        loadChartOfAccounts();
        
        // Add remove functionality
        newRow.querySelector('.remove-entry-btn').addEventListener('click', function() {
            newRow.remove();
            calculateJournalTotals();
        });
        
        // Show remove buttons if more than one row
        if (rowCount > 0) {
            document.querySelectorAll('.remove-entry-btn').forEach(btn => {
                btn.style.display = 'block';
            });
        }
    }
    
    function calculateJournalTotals() {
        const debitInputs = document.querySelectorAll('.debit-amount');
        const creditInputs = document.querySelectorAll('.credit-amount');
        
        let totalDebits = 0;
        let totalCredits = 0;
        
        debitInputs.forEach(input => {
            totalDebits += parseFloat(input.value) || 0;
        });
        
        creditInputs.forEach(input => {
            totalCredits += parseFloat(input.value) || 0;
        });
        
        document.getElementById('totalDebits').textContent = totalDebits.toFixed(2);
        document.getElementById('totalCredits').textContent = totalCredits.toFixed(2);
        
        const balanceCheck = document.getElementById('balanceCheck');
        const difference = Math.abs(totalDebits - totalCredits);
        
        if (difference < 0.01) {
            balanceCheck.innerHTML = '<span class="text-success"><i class="fas fa-check"></i> Balanced</span>';
        } else {
            balanceCheck.innerHTML = '<span class="text-danger"><i class="fas fa-exclamation-triangle"></i> Out of balance by ' + formatCurrency(difference) + '</span>';
        }
    }
    
    async function saveJournalEntry() {
        const form = document.getElementById('journalEntryForm');
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        // Collect entries
        const entries = [];
        const rows = document.querySelectorAll('.journal-entry-row');
        
        rows.forEach(row => {
            const accountId = row.querySelector('.account-select').value;
            const debit = parseFloat(row.querySelector('.debit-amount').value) || 0;
            const credit = parseFloat(row.querySelector('.credit-amount').value) || 0;
            
            if (accountId && (debit > 0 || credit > 0)) {
                entries.push({
                    account_id: parseInt(accountId),
                    debit: debit,
                    credit: credit,
                    description: document.getElementById('journalDescription').value
                });
            }
        });
        
        if (entries.length < 2) {
            alert('Journal entry must have at least 2 accounts');
            return;
        }
        
        const journalData = {
            description: document.getElementById('journalDescription').value,
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
                bootstrap.Modal.getInstance(document.getElementById('journalEntryModal')).hide();
                form.reset();
                loadJournalEntries();
                loadTrialBalance();
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
    
    async function saveBankAccount() {
        const form = document.getElementById('bankAccountForm');
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        const accountData = {
            account_name: document.getElementById('bankAccountName').value,
            account_number: document.getElementById('bankAccountNumber').value,
            bank_name: document.getElementById('bankName').value,
            account_type: document.getElementById('bankAccountType').value,
            current_balance: parseFloat(document.getElementById('currentBalance').value) || 0
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
                bootstrap.Modal.getInstance(document.getElementById('bankAccountModal')).hide();
                form.reset();
                loadBankAccounts();
                populateBankAccountSelects();
                alert('Bank account created successfully!');
            } else {
                const error = await response.json();
                alert('Error: ' + (error.error || 'Failed to create bank account'));
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error creating bank account');
        }
    }
    
    async function saveBankTransfer() {
        const form = document.getElementById('bankTransferForm');
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        const transferData = {
            from_account_id: parseInt(document.getElementById('fromAccount').value),
            to_account_id: parseInt(document.getElementById('toAccount').value),
            amount: parseFloat(document.getElementById('transferAmount').value),
            transfer_fee: parseFloat(document.getElementById('transferFee').value) || 0,
            description: document.getElementById('transferDescription').value
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
                bootstrap.Modal.getInstance(document.getElementById('bankTransferModal')).hide();
                form.reset();
                loadBankTransfers();
                loadBankAccounts();
                alert('Bank transfer processed successfully!');
            } else {
                const error = await response.json();
                alert('Error: ' + (error.error || 'Failed to process transfer'));
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error processing transfer');
        }
    }
    
    // Utility functions
    function formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString();
    }
    
    function formatCurrency(amount) {
        return new Intl.NumberFormat('en-TZ', {
            style: 'currency',
            currency: 'TZS',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount || 0);
    }
    
    // Global functions for buttons
    window.editAccount = function(accountId) {
        // Implementation for editing accounts
        console.log('Edit account:', accountId);
    };
    
    window.viewJournalEntry = function(journalId) {
        // Implementation for viewing journal entries
        console.log('View journal entry:', journalId);
    };
});
