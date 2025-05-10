// Function to get theme-consistent chart colors
function getThemeColors() {
    const theme = document.body.getAttribute('data-theme-value') || 'tanzanite';
    
    // Default color palette based on tanzanite theme
    const colors = {
        primary: 'rgba(76, 80, 197, 0.8)',
        secondary: 'rgba(108, 117, 125, 0.8)',
        success: 'rgba(40, 167, 69, 0.8)',
        info: 'rgba(23, 162, 184, 0.8)',
        warning: 'rgba(255, 193, 7, 0.8)',
        danger: 'rgba(220, 53, 69, 0.8)',
        light: 'rgba(248, 249, 250, 0.8)',
        dark: 'rgba(52, 58, 64, 0.8)',
        purple: 'rgba(153, 102, 255, 0.8)',
        orange: 'rgba(255, 159, 64, 0.8)',
        teal: 'rgba(32, 201, 151, 0.8)',
        indigo: 'rgba(102, 16, 242, 0.8)'
    };
    
    return colors;
}

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const totalItemsElement = document.getElementById('total-items');
    const totalStockElement = document.getElementById('total-stock');
    const lowStockCountElement = document.getElementById('low-stock-count');
    const inventoryValueElement = document.getElementById('inventory-value');
    const lowStockTableElement = document.getElementById('low-stock-table');
    const onDemandProductsTableElement = document.getElementById('on-demand-products-table');
    const inventoryHealthContainer = document.getElementById('inventory-health-container');
    
    // Financial Elements
    const monthlyIncomeElement = document.getElementById('monthly-income');
    const monthlyExpensesElement = document.getElementById('monthly-expenses');
    const monthlyProfitElement = document.getElementById('monthly-profit');
    const financialSummaryChartElement = document.getElementById('financialSummaryChart');
    
    // Charts
    let stockChart = null;
    let valueChart = null;
    let healthDonutChart = null;
    let financialChart = null;
    
    // Load dashboard data
    loadDashboardData();
    loadOnDemandProducts();
    loadFinancialSummary();
    
    // Calculate inventory health based on quantity
    function calculateInventoryHealth(quantity) {
        if (quantity <= 0) {
            return {
                status: 'critical',
                label: 'Out of Stock',
                color: 'danger',
                icon: 'exclamation-circle',
                percentage: 0,
                bgColor: '#dc3545'
            };
        } else if (quantity <= 5) {
            return {
                status: 'low',
                label: 'Low Stock',
                color: 'warning',
                icon: 'exclamation-triangle',
                percentage: 25,
                bgColor: '#ffc107'
            };
        } else if (quantity <= 10) {
            return {
                status: 'medium',
                label: 'Medium Stock',
                color: 'info',
                icon: 'info-circle',
                percentage: 50,
                bgColor: '#0dcaf0'
            };
        } else if (quantity <= 20) {
            return {
                status: 'good',
                label: 'Good Stock',
                color: 'primary',
                icon: 'check-circle',
                percentage: 75,
                bgColor: '#0d6efd'
            };
        } else {
            return {
                status: 'optimal',
                label: 'Optimal Stock',
                color: 'success',
                icon: 'check-double',
                percentage: 100,
                bgColor: '#198754'
            };
        }
    }
    
    // Generate health indicator HTML
    function generateHealthIndicator(quantity) {
        const health = calculateInventoryHealth(quantity);
        
        return `
            <div class="inventory-health">
                <div class="health-indicator">
                    <div class="progress" style="height: 8px;" title="${health.label}">
                        <div class="progress-bar bg-${health.color}" role="progressbar" 
                             style="width: ${health.percentage}%" 
                             aria-valuenow="${health.percentage}" aria-valuemin="0" aria-valuemax="100"></div>
                    </div>
                    <div class="mt-1 d-flex align-items-center">
                        <i class="fas fa-${health.icon} text-${health.color} me-1"></i>
                        <span class="small ${quantity <= 5 ? 'fw-bold' : ''}">${quantity} ${quantity <= 0 ? health.label : 'units'}</span>
                    </div>
                </div>
            </div>
        `;
    }
    
    function loadDashboardData() {
        // Load stock status report
        fetch('/api/reports/stock-status')
            .then(response => response.json())
            .then(data => {
                updateDashboardSummary(data);
                updateLowStockTable(data.low_stock_items);
            })
            .catch(error => {
                console.error('Error loading stock status report:', error);
            });
        
        // Load category breakdown for charts
        fetch('/api/reports/category-breakdown')
            .then(response => response.json())
            .then(data => {
                createStockChart(data);
                createValueChart(data);
            })
            .catch(error => {
                console.error('Error loading category breakdown:', error);
            });
    }
    
    function updateDashboardSummary(data) {
        // Update summary cards
        totalItemsElement.textContent = data.total_items;
        totalStockElement.textContent = data.total_stock;
        lowStockCountElement.textContent = data.low_stock_items_count;
        inventoryValueElement.innerHTML = '<span class="currency-symbol">TZS</span> ' + data.total_inventory_value.toLocaleString();
        
        // Create inventory health overview if container exists
        if (inventoryHealthContainer) {
            // Calculate health stats
            const healthStats = calculateInventoryHealthStats(data);
            createInventoryHealthOverview(healthStats);
        }
    }
    
    function calculateInventoryHealthStats(data) {
        // Calculate inventory health statistics from stock status data
        let healthStats = {
            critical: 0,
            low: 0,
            medium: 0,
            good: 0,
            optimal: 0
        };
        
        // Process all items to determine their health
        if (data.all_items && Array.isArray(data.all_items)) {
            data.all_items.forEach(item => {
                const health = calculateInventoryHealth(item.quantity);
                healthStats[health.status]++;
            });
        } else if (data.low_stock_items && Array.isArray(data.low_stock_items)) {
            // If we only have low stock items, estimate based on what we know
            data.low_stock_items.forEach(item => {
                const health = calculateInventoryHealth(item.quantity);
                healthStats[health.status]++;
            });
            
            // Estimate remaining items as good/optimal
            const remainingItems = data.total_items - data.low_stock_items.length;
            if (remainingItems > 0) {
                healthStats.good = Math.floor(remainingItems * 0.4);
                healthStats.optimal = remainingItems - healthStats.good;
            }
        }
        
        return healthStats;
    }
    
    function createInventoryHealthOverview(healthStats) {
        // Create health overview cards and chart
        const healthCategories = [
            { status: 'critical', label: 'Out of Stock', color: 'danger', icon: 'exclamation-circle', bgColor: '#dc3545' },
            { status: 'low', label: 'Low Stock', color: 'warning', icon: 'exclamation-triangle', bgColor: '#ffc107' },
            { status: 'medium', label: 'Medium Stock', color: 'info', icon: 'info-circle', bgColor: '#0dcaf0' },
            { status: 'good', label: 'Good Stock', color: 'primary', icon: 'check-circle', bgColor: '#0d6efd' },
            { status: 'optimal', label: 'Optimal Stock', color: 'success', icon: 'check-double', bgColor: '#198754' }
        ];
        
        // Create HTML for health overview
        let healthOverviewHTML = '<div class="row">';
        
        // Create a card for each health category
        healthCategories.forEach(category => {
            const count = healthStats[category.status] || 0;
            healthOverviewHTML += `
                <div class="col">
                    <div class="card summary-card text-center mb-3">
                        <div class="card-body">
                            <div class="d-flex align-items-center justify-content-center mb-2">
                                <i class="fas fa-${category.icon} text-${category.color} fa-2x me-2"></i>
                                <h3 class="m-0">${count}</h3>
                            </div>
                            <p class="card-text text-${category.color}">${category.label}</p>
                        </div>
                    </div>
                </div>
            `;
        });
        
        healthOverviewHTML += '</div>';
        
        // Create donut chart canvas
        healthOverviewHTML += `
            <div class="row mt-3">
                <div class="col-md-12">
                    <div class="card chart-card">
                        <div class="card-header">
                            <h5 class="card-title mb-0">Inventory Health Distribution</h5>
                        </div>
                        <div class="card-body">
                            <canvas id="healthDonut" height="200"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Update DOM with health overview
        inventoryHealthContainer.innerHTML = healthOverviewHTML;
        
        // Create donut chart
        const ctx = document.getElementById('healthDonut').getContext('2d');
        
        if (healthDonutChart) {
            healthDonutChart.destroy();
        }
        
        healthDonutChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: healthCategories.map(c => c.label),
                datasets: [{
                    data: healthCategories.map(c => healthStats[c.status] || 0),
                    backgroundColor: healthCategories.map(c => c.bgColor),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim() || '#333'
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    function updateLowStockTable(lowStockItems) {
        if (lowStockItems && lowStockItems.length > 0) {
            let tableHtml = '';
            
            // Sort by quantity (lowest first)
            lowStockItems.sort((a, b) => a.quantity - b.quantity);
            
            // Take only top 10 items
            const itemsToShow = lowStockItems.slice(0, 10);
            
            itemsToShow.forEach(item => {
                const quantityClass = item.quantity === 0 ? 'bg-danger' : 'bg-warning';
                
                tableHtml += `
                <tr>
                    <td>
                        <a href="/item/${item.id}" class="text-decoration-none">
                            ${item.name}
                        </a>
                    </td>
                    <td>${item.sku || ''}</td>
                    <td>${item.category || 'Uncategorized'}</td>
                    <td>${generateHealthIndicator(item.quantity)}</td>
                    <td>
                        <small class="text-muted">Retail: </small><span class="currency-symbol">TZS</span> ${item.selling_price_retail ? item.selling_price_retail.toLocaleString() : '0'}<br>
                        <small class="text-muted">Wholesale: </small><span class="currency-symbol">TZS</span> ${item.selling_price_wholesale ? item.selling_price_wholesale.toLocaleString() : '0'}
                    </td>
                    <td>
                        <a href="/item/${item.id}" class="btn btn-sm btn-primary">
                            <i class="fas fa-edit"></i> Update
                        </a>
                    </td>
                </tr>
                `;
            });
            
            lowStockTableElement.innerHTML = tableHtml;
        } else {
            lowStockTableElement.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center">No low stock items found</td>
                </tr>
            `;
        }
    }
    
    function createStockChart(categoryData) {
        // Prepare data for chart
        const categories = Object.keys(categoryData);
        const quantities = categories.map(category => categoryData[category].total_quantity);
        
        // Get canvas context
        const ctx = document.getElementById('stockChart').getContext('2d');
        
        // Destroy existing chart if it exists
        if (stockChart) {
            stockChart.destroy();
        }
        
        // Create new chart
        stockChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: categories,
                datasets: [{
                    label: 'Stock Quantity',
                    data: quantities,
                    backgroundColor: getThemeColors().primary,
                    borderColor: getThemeColors().info,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Stock: ${context.raw}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(76, 80, 197, 0.06)'
                        },
                        ticks: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim() || '#555'
                        },
                        title: {
                            display: true,
                            text: 'Quantity',
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim() || '#333',
                            font: {
                                weight: '600'
                            }
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(76, 80, 197, 0.04)'
                        },
                        ticks: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim() || '#555'
                        },
                        title: {
                            display: true,
                            text: 'Category',
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim() || '#333',
                            font: {
                                weight: '600'
                            }
                        }
                    }
                }
            }
        });
    }
    
    function createValueChart(categoryData) {
        // Prepare data for chart
        const categories = Object.keys(categoryData);
        const values = categories.map(category => categoryData[category].total_value);
        
        // Get canvas context
        const ctx = document.getElementById('valueChart').getContext('2d');
        
        // Destroy existing chart if it exists
        if (valueChart) {
            valueChart.destroy();
        }
        
        // Create new chart
        valueChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: categories,
                datasets: [{
                    data: values,
                    backgroundColor: [
                        getThemeColors().primary,
                        getThemeColors().info,
                        getThemeColors().warning,
                        getThemeColors().success,
                        getThemeColors().purple,
                        getThemeColors().orange,
                        getThemeColors().teal,
                        getThemeColors().indigo,
                        getThemeColors().secondary,
                        getThemeColors().danger
                    ],
                    borderColor: [
                        getThemeColors().primary.replace('0.8', '1'),
                        getThemeColors().info.replace('0.8', '1'),
                        getThemeColors().warning.replace('0.8', '1'),
                        getThemeColors().success.replace('0.8', '1'),
                        getThemeColors().purple.replace('0.8', '1'),
                        getThemeColors().orange.replace('0.8', '1'),
                        getThemeColors().teal.replace('0.8', '1'),
                        getThemeColors().indigo.replace('0.8', '1'),
                        getThemeColors().secondary.replace('0.8', '1'),
                        getThemeColors().danger.replace('0.8', '1')
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim() || '#333',
                            usePointStyle: true,
                            padding: 15,
                            font: {
                                family: getComputedStyle(document.documentElement).getPropertyValue('--body-font').trim() || "'Nunito', sans-serif"
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw;
                                const label = context.label || '';
                                const percentage = ((value / values.reduce((a, b) => a + b, 0)) * 100).toFixed(1);
                                return `${label}: TZS ${value.toLocaleString()} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    function loadOnDemandProducts() {
        // Fetch active on-demand products
        fetch('/api/on-demand?active_only=true')
            .then(response => response.json())
            .then(products => {
                displayOnDemandProducts(products);
            })
            .catch(error => {
                console.error('Error loading on-demand products:', error);
                onDemandProductsTableElement.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center text-danger">
                            <i class="fas fa-exclamation-circle me-2"></i> Error loading on-demand products
                        </td>
                    </tr>
                `;
            });
    }
    
    function displayOnDemandProducts(products) {
        if (products.length === 0) {
            onDemandProductsTableElement.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center">No on-demand products found</td>
                </tr>
            `;
            return;
        }
        
        // Sort products by name for consistent display
        products.sort((a, b) => a.name.localeCompare(b.name));
        
        // Show only the first 10 products for dashboard
        const displayProducts = products.slice(0, 10);
        
        let html = '';
        
        displayProducts.forEach(product => {
            const statusBadge = product.is_active 
                ? '<span class="status-badge status-active">Active</span>' 
                : '<span class="status-badge status-inactive">Inactive</span>';
            
            html += `
                <tr>
                    <td>
                        <a href="/on-demand#product-${product.id}" class="text-decoration-none">
                            ${product.name}
                        </a>
                    </td>
                    <td>${product.category || 'Uncategorized'}</td>
                    <td><span class="currency-symbol">TZS</span> ${product.base_price.toLocaleString()}</td>
                    <td>${product.production_time || 0} hours</td>
                    <td>${statusBadge}</td>
                    <td>
                        <a href="/on-demand" class="btn btn-sm btn-primary btn-action">
                            <i class="fas fa-edit"></i> View
                        </a>
                    </td>
                </tr>
            `;
        });
        
        if (products.length > 10) {
            html += `
                <tr>
                    <td colspan="6" class="text-center">
                        <a href="/on-demand" class="btn btn-sm btn-outline-secondary">
                            View all ${products.length} on-demand products
                        </a>
                    </td>
                </tr>
            `;
        }
        
        onDemandProductsTableElement.innerHTML = html;
    }
    
    // Load financial summary data for dashboard
    function loadFinancialSummary() {
        // Get current date
        const today = new Date();
        const year = today.getFullYear();
        const month = today.getMonth() + 1;
        
        // Get first and last day of current month
        const firstDay = new Date(year, month - 1, 1);
        const lastDay = new Date(year, month, 0);
        
        // Format dates as YYYY-MM-DD
        const startDate = firstDay.toISOString().slice(0, 10);
        const endDate = lastDay.toISOString().slice(0, 10);
        
        // Load monthly transactions data
        fetch(`/api/finance/transactions?start_date=${startDate}&end_date=${endDate}`)
            .then(response => response.json())
            .then(data => {
                updateFinancialSummary(data.summary);
            })
            .catch(error => {
                console.error('Error loading financial summary:', error);
            });
        
        // Load yearly data for chart
        fetch(`/api/finance/summaries/monthly?year=${year}`)
            .then(response => response.json())
            .then(data => {
                createFinancialChart(data);
            })
            .catch(error => {
                console.error('Error loading monthly financial data:', error);
            });
    }
    
    // Update financial summary on dashboard
    function updateFinancialSummary(summary) {
        if (!monthlyIncomeElement || !monthlyExpensesElement || !monthlyProfitElement) {
            return;
        }
        
        monthlyIncomeElement.textContent = summary.total_income.toLocaleString();
        monthlyExpensesElement.textContent = summary.total_expenses.toLocaleString();
        monthlyProfitElement.textContent = summary.net_profit.toLocaleString();
        
        // Add color to profit value
        if (summary.net_profit > 0) {
            monthlyProfitElement.classList.add('text-success');
            monthlyProfitElement.classList.remove('text-danger');
        } else if (summary.net_profit < 0) {
            monthlyProfitElement.classList.add('text-danger');
            monthlyProfitElement.classList.remove('text-success');
        } else {
            monthlyProfitElement.classList.remove('text-success');
            monthlyProfitElement.classList.remove('text-danger');
        }
    }
    
    // Create financial summary chart
    function createFinancialChart(data) {
        if (!financialSummaryChartElement) {
            return;
        }
        
        const ctx = financialSummaryChartElement.getContext('2d');
        
        // Destroy existing chart if it exists
        if (financialChart) {
            financialChart.destroy();
        }
        
        // Extract data for chart
        const months = data.monthly_data.map(item => item.month_name);
        const incomeData = data.monthly_data.map(item => item.income);
        const expenseData = data.monthly_data.map(item => item.expenses);
        const profitData = data.monthly_data.map(item => item.profit);
        
        // Create new chart
        financialChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: months,
                datasets: [
                    {
                        label: 'Income',
                        data: incomeData,
                        backgroundColor: getThemeColors().success,
                        borderColor: getThemeColors().success.replace('0.8', '1'),
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
                            color: 'rgba(76, 80, 197, 0.08)'
                        },
                        ticks: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim() || '#555',
                            callback: function(value) {
                                return 'TZS ' + value.toLocaleString();
                            }
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(76, 80, 197, 0.06)'
                        },
                        ticks: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim() || '#555'
                        }
                    }
                },
                plugins: {
                    legend: {
                        labels: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim() || '#333',
                            usePointStyle: true,
                            padding: 15
                        }
                    },
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
});
