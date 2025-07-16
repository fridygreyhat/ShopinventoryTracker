
document.addEventListener('DOMContentLoaded', function() {
    // Event listeners for report generation buttons
    document.getElementById('generateSalesReportBtn').addEventListener('click', generateSalesReport);
    document.getElementById('generateStockReportBtn').addEventListener('click', generateStockReport);
    document.getElementById('generateAccountingReportBtn').addEventListener('click', generateAccountingReport);
    
    // Date range selectors
    document.getElementById('salesDateRange').addEventListener('change', function() {
        toggleCustomDateRange('customDateRange', this.value === 'custom');
    });
    
    document.getElementById('accountingPeriod').addEventListener('change', function() {
        toggleCustomDateRange('customAccountingPeriod', this.value === 'custom');
    });

    function toggleCustomDateRange(elementId, show) {
        const element = document.getElementById(elementId);
        if (show) {
            element.classList.remove('d-none');
        } else {
            element.classList.add('d-none');
        }
    }

    function generateSalesReport() {
        const reportType = document.getElementById('salesReportType').value;
        const dateRange = document.getElementById('salesDateRange').value;
        
        hideAllReportDisplays();
        document.getElementById('salesReportsDisplay').classList.remove('d-none');
        document.getElementById('salesReportTitle').textContent = getSalesReportTitle(reportType);
        
        let apiUrl = '/api/sales';
        let params = new URLSearchParams({ type: reportType, range: dateRange });
        
        if (dateRange === 'custom') {
            const startDate = document.getElementById('salesStartDate').value;
            const endDate = document.getElementById('salesEndDate').value;
            if (startDate && endDate) {
                params.append('start_date', startDate);
                params.append('end_date', endDate);
            }
        }
        
        fetch(`${apiUrl}?${params}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    displaySalesReport(data.reports, reportType);
                } else {
                    showError('Failed to generate sales report');
                }
            })
            .catch(error => {
                console.error('Error generating sales report:', error);
                showError('Error generating sales report');
            });
    }

    function generateStockReport() {
        const reportType = document.getElementById('stockReportType').value;
        const threshold = document.getElementById('lowStockThreshold').value;
        
        hideAllReportDisplays();
        document.getElementById('stockReportsDisplay').classList.remove('d-none');
        document.getElementById('stockReportTitle').textContent = getStockReportTitle(reportType);
        
        let apiUrl = '/api/reports/stock';
        let params = new URLSearchParams({ type: reportType, threshold: threshold });
        
        fetch(`${apiUrl}?${params}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    displayStockReport(data, reportType);
                } else {
                    showError('Failed to generate stock report');
                }
            })
            .catch(error => {
                console.error('Error generating stock report:', error);
                showError('Error generating stock report');
            });
    }

    function generateAccountingReport() {
        const reportType = document.getElementById('accountingReportType').value;
        const period = document.getElementById('accountingPeriod').value;
        
        hideAllReportDisplays();
        document.getElementById('accountingReportsDisplay').classList.remove('d-none');
        document.getElementById('accountingReportTitle').textContent = getAccountingReportTitle(reportType);
        
        let apiUrl = '/api/reports/accounting';
        let params = new URLSearchParams({ type: reportType, period: period });
        
        if (period === 'custom') {
            const startDate = document.getElementById('accountingStartDate').value;
            const endDate = document.getElementById('accountingEndDate').value;
            if (startDate && endDate) {
                params.append('start_date', startDate);
                params.append('end_date', endDate);
            }
        }
        
        fetch(`${apiUrl}?${params}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    displayAccountingReport(data, reportType);
                } else {
                    showError('Failed to generate accounting report');
                }
            })
            .catch(error => {
                console.error('Error generating accounting report:', error);
                showError('Error generating accounting report');
            });
    }

    function hideAllReportDisplays() {
        document.querySelectorAll('.report-display').forEach(el => el.classList.add('d-none'));
    }

    function displaySalesReport(data, reportType) {
        const tableHead = document.getElementById('salesTableHead');
        const tableBody = document.getElementById('salesTableBody');
        
        if (reportType === 'completed-sales') {
            tableHead.innerHTML = `
                <tr>
                    <th>Sale Number</th>
                    <th>Date</th>
                    <th>Customer</th>
                    <th>Items</th>
                    <th>Total Amount</th>
                    <th>Payment Method</th>
                </tr>
            `;
            
            let tableHtml = '';
            data.forEach(sale => {
                tableHtml += `
                    <tr>
                        <td>${sale.sale_number}</td>
                        <td>${new Date(sale.created_at).toLocaleDateString()}</td>
                        <td>${sale.customer_name || 'Walk-in Customer'}</td>
                        <td>${sale.items_count}</td>
                        <td><span class="currency-symbol">TZS</span> ${parseFloat(sale.total_amount).toLocaleString()}</td>
                        <td><span class="badge bg-success">${sale.payment_method}</span></td>
                    </tr>
                `;
            });
            tableBody.innerHTML = tableHtml || '<tr><td colspan="6" class="text-center">No completed sales found</td></tr>';
        } else if (reportType === 'pending-sales') {
            tableHead.innerHTML = `
                <tr>
                    <th>Sale Number</th>
                    <th>Date</th>
                    <th>Customer</th>
                    <th>Items</th>
                    <th>Total Amount</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>
            `;
            
            let tableHtml = '';
            data.forEach(sale => {
                tableHtml += `
                    <tr>
                        <td>${sale.sale_number}</td>
                        <td>${new Date(sale.created_at).toLocaleDateString()}</td>
                        <td>${sale.customer_name || 'Walk-in Customer'}</td>
                        <td>${sale.items_count}</td>
                        <td><span class="currency-symbol">TZS</span> ${parseFloat(sale.total_amount).toLocaleString()}</td>
                        <td><span class="badge bg-warning">Pending</span></td>
                        <td>
                            <button class="btn btn-sm btn-success" onclick="completeSale(${sale.id})">
                                <i class="fas fa-check"></i> Complete
                            </button>
                        </td>
                    </tr>
                `;
            });
            tableBody.innerHTML = tableHtml || '<tr><td colspan="7" class="text-center">No pending sales found</td></tr>';
        }
    }

    function displayStockReport(data, reportType) {
        const tableHead = document.getElementById('stockTableHead');
        const tableBody = document.getElementById('stockTableBody');
        const summaryCards = document.getElementById('stockSummaryCards');
        
        if (reportType === 'stock-available') {
            // Update summary cards
            document.getElementById('total-items').textContent = data.total_items || 0;
            document.getElementById('total-stock').textContent = data.total_stock || 0;
            document.getElementById('low-stock-count').textContent = data.low_stock_count || 0;
            document.getElementById('out-of-stock-count').textContent = data.out_of_stock_count || 0;
            
            summaryCards.classList.remove('d-none');
            
            tableHead.innerHTML = `
                <tr>
                    <th>Name</th>
                    <th>SKU</th>
                    <th>Category</th>
                    <th>Current Stock</th>
                    <th>Minimum Stock</th>
                    <th>Status</th>
                    <th>Value</th>
                </tr>
            `;
            
            let tableHtml = '';
            data.items.forEach(item => {
                const status = item.stock_quantity <= 0 ? 'Out of Stock' : 
                              item.stock_quantity <= item.minimum_stock ? 'Low Stock' : 'In Stock';
                const statusClass = item.stock_quantity <= 0 ? 'bg-danger' : 
                                   item.stock_quantity <= item.minimum_stock ? 'bg-warning' : 'bg-success';
                
                tableHtml += `
                    <tr>
                        <td>${item.name}</td>
                        <td>${item.sku || ''}</td>
                        <td>${item.category || 'Uncategorized'}</td>
                        <td>${item.stock_quantity}</td>
                        <td>${item.minimum_stock || 0}</td>
                        <td><span class="badge ${statusClass}">${status}</span></td>
                        <td><span class="currency-symbol">TZS</span> ${(item.stock_quantity * item.price).toLocaleString()}</td>
                    </tr>
                `;
            });
            tableBody.innerHTML = tableHtml || '<tr><td colspan="7" class="text-center">No items found</td></tr>';
        } else if (reportType === 'stock-transactions') {
            summaryCards.classList.add('d-none');
            
            tableHead.innerHTML = `
                <tr>
                    <th>Date</th>
                    <th>Item</th>
                    <th>Type</th>
                    <th>Quantity</th>
                    <th>Reason</th>
                    <th>Reference</th>
                </tr>
            `;
            
            let tableHtml = '';
            data.transactions.forEach(transaction => {
                const typeClass = transaction.type === 'in' ? 'bg-success' : 'bg-danger';
                const typeText = transaction.type === 'in' ? 'Stock In' : 'Stock Out';
                
                tableHtml += `
                    <tr>
                        <td>${new Date(transaction.date).toLocaleDateString()}</td>
                        <td>${transaction.item_name}</td>
                        <td><span class="badge ${typeClass}">${typeText}</span></td>
                        <td>${transaction.quantity}</td>
                        <td>${transaction.reason}</td>
                        <td>${transaction.reference || ''}</td>
                    </tr>
                `;
            });
            tableBody.innerHTML = tableHtml || '<tr><td colspan="6" class="text-center">No stock transactions found</td></tr>';
        } else if (reportType === 'stock-issues') {
            summaryCards.classList.add('d-none');
            
            tableHead.innerHTML = `
                <tr>
                    <th>Date</th>
                    <th>Item</th>
                    <th>Issue Type</th>
                    <th>Quantity</th>
                    <th>Value Lost</th>
                    <th>Notes</th>
                </tr>
            `;
            
            let tableHtml = '';
            data.issues.forEach(issue => {
                const issueClass = issue.type === 'expired' ? 'bg-warning' : 
                                  issue.type === 'broken' ? 'bg-danger' : 'bg-dark';
                
                tableHtml += `
                    <tr>
                        <td>${new Date(issue.date).toLocaleDateString()}</td>
                        <td>${issue.item_name}</td>
                        <td><span class="badge ${issueClass}">${issue.type.charAt(0).toUpperCase() + issue.type.slice(1)}</span></td>
                        <td>${issue.quantity}</td>
                        <td><span class="currency-symbol">TZS</span> ${issue.value_lost.toLocaleString()}</td>
                        <td>${issue.notes || ''}</td>
                    </tr>
                `;
            });
            tableBody.innerHTML = tableHtml || '<tr><td colspan="6" class="text-center">No stock issues found</td></tr>';
        }
    }

    function displayAccountingReport(data, reportType) {
        const tableHead = document.getElementById('accountingTableHead');
        const tableBody = document.getElementById('accountingTableBody');
        const financialSummary = document.getElementById('financialSummary');
        
        if (reportType === 'profit-loss' || reportType === 'income-statement') {
            financialSummary.classList.remove('d-none');
            
            const metrics = document.getElementById('financialMetrics');
            metrics.innerHTML = `
                <div class="row mb-2">
                    <div class="col-6 fw-bold">Total Revenue:</div>
                    <div class="col-6"><span class="currency-symbol">TZS</span> ${data.revenue.toLocaleString()}</div>
                </div>
                <div class="row mb-2">
                    <div class="col-6 fw-bold">Total Expenses:</div>
                    <div class="col-6"><span class="currency-symbol">TZS</span> ${data.expenses.toLocaleString()}</div>
                </div>
                <div class="row mb-2">
                    <div class="col-6 fw-bold">Net Profit:</div>
                    <div class="col-6 ${data.net_profit >= 0 ? 'text-success' : 'text-danger'}">
                        <span class="currency-symbol">TZS</span> ${data.net_profit.toLocaleString()}
                    </div>
                </div>
                <div class="row">
                    <div class="col-6 fw-bold">Profit Margin:</div>
                    <div class="col-6">${data.profit_margin.toFixed(2)}%</div>
                </div>
            `;
            
            tableHead.innerHTML = `
                <tr>
                    <th>Account</th>
                    <th>Amount</th>
                    <th>Percentage</th>
                </tr>
            `;
            
            let tableHtml = '';
            data.breakdown.forEach(item => {
                tableHtml += `
                    <tr>
                        <td>${item.account}</td>
                        <td><span class="currency-symbol">TZS</span> ${item.amount.toLocaleString()}</td>
                        <td>${item.percentage.toFixed(2)}%</td>
                    </tr>
                `;
            });
            tableBody.innerHTML = tableHtml;
        } else {
            financialSummary.classList.add('d-none');
            
            if (reportType === 'balance-sheet') {
                tableHead.innerHTML = `
                    <tr>
                        <th>Account Type</th>
                        <th>Account</th>
                        <th>Amount</th>
                    </tr>
                `;
            } else if (reportType === 'expenses') {
                tableHead.innerHTML = `
                    <tr>
                        <th>Date</th>
                        <th>Category</th>
                        <th>Description</th>
                        <th>Amount</th>
                    </tr>
                `;
            }
            
            let tableHtml = '';
            data.items.forEach(item => {
                if (reportType === 'balance-sheet') {
                    tableHtml += `
                        <tr>
                            <td>${item.type}</td>
                            <td>${item.account}</td>
                            <td><span class="currency-symbol">TZS</span> ${item.amount.toLocaleString()}</td>
                        </tr>
                    `;
                } else if (reportType === 'expenses') {
                    tableHtml += `
                        <tr>
                            <td>${new Date(item.date).toLocaleDateString()}</td>
                            <td>${item.category}</td>
                            <td>${item.description}</td>
                            <td><span class="currency-symbol">TZS</span> ${item.amount.toLocaleString()}</td>
                        </tr>
                    `;
                }
            });
            tableBody.innerHTML = tableHtml || '<tr><td colspan="4" class="text-center">No data found</td></tr>';
        }
    }

    function getSalesReportTitle(type) {
        const titles = {
            'completed-sales': 'Completed Sales Report',
            'pending-sales': 'Pending Sales Report'
        };
        return titles[type] || 'Sales Report';
    }

    function getStockReportTitle(type) {
        const titles = {
            'stock-available': 'Stock Availability Report',
            'stock-transactions': 'Stock Transactions Report',
            'stock-issues': 'Stock Issues Report'
        };
        return titles[type] || 'Stock Report';
    }

    function getAccountingReportTitle(type) {
        const titles = {
            'profit-loss': 'Profit & Loss Statement',
            'balance-sheet': 'Balance Sheet',
            'income-statement': 'Income Statement',
            'expenses': 'Expenses Report'
        };
        return titles[type] || 'Accounting Report';
    }

    function showError(message) {
        // You can implement a toast or alert system here
        alert(message);
    }

    // Helper function for completing sales (for pending sales report)
    window.completeSale = function(saleId) {
        if (confirm('Are you sure you want to complete this sale?')) {
            // Complete sale functionality removed - sales are created as completed
            alert('This sale is already marked as completed.');
        }
    };
});
