// Function to get theme-consistent chart colors
function getThemeColors() {
    const theme = document.body.getAttribute('data-theme-value') || 'tanzanite';

    // Theme-specific color palettes
    const themePalettes = {
        tanzanite: {
            primary: 'rgba(76, 80, 197, 0.8)',
            secondary: 'rgba(65, 193, 224, 0.8)',
            accent: 'rgba(255, 121, 80, 0.8)',
            success: 'rgba(50, 184, 115, 0.8)',
            warning: 'rgba(255, 167, 38, 0.8)',
            danger: 'rgba(240, 74, 74, 0.8)',
            info: 'rgba(56, 137, 247, 0.8)',
        },
        forest: {
            primary: 'rgba(46, 139, 87, 0.8)',
            secondary: 'rgba(76, 175, 80, 0.8)',
            accent: 'rgba(255, 193, 7, 0.8)',
            success: 'rgba(32, 201, 151, 0.8)',
            warning: 'rgba(255, 152, 0, 0.8)',
            danger: 'rgba(244, 67, 54, 0.8)',
            info: 'rgba(3, 169, 244, 0.8)',
        },
        ocean: {
            primary: 'rgba(0, 119, 182, 0.8)',
            secondary: 'rgba(0, 180, 216, 0.8)',
            accent: 'rgba(144, 224, 239, 0.8)',
            success: 'rgba(64, 192, 179, 0.8)',
            warning: 'rgba(255, 209, 102, 0.8)',
            danger: 'rgba(240, 74, 74, 0.8)',
            info: 'rgba(72, 202, 228, 0.8)',
        },
        sunset: {
            primary: 'rgba(235, 94, 40, 0.8)',
            secondary: 'rgba(250, 163, 7, 0.8)',
            accent: 'rgba(255, 195, 0, 0.8)',
            success: 'rgba(102, 187, 106, 0.8)',
            warning: 'rgba(255, 183, 77, 0.8)',
            danger: 'rgba(229, 57, 53, 0.8)',
            info: 'rgba(79, 195, 247, 0.8)',
        },
        dark: {
            primary: 'rgba(86, 90, 207, 0.8)',
            secondary: 'rgba(108, 117, 125, 0.8)',
            accent: 'rgba(255, 121, 80, 0.8)',
            success: 'rgba(72, 187, 120, 0.8)',
            warning: 'rgba(237, 185, 45, 0.8)',
            danger: 'rgba(231, 76, 60, 0.8)',
            info: 'rgba(52, 152, 219, 0.8)',
        }
    };

    // Get colors for current theme or fallback to tanzanite
    const colors = themePalettes[theme] || themePalettes.tanzanite;

    // Add common colors and neutral tones
    return {
        ...colors,
        light: 'rgba(248, 249, 250, 0.8)',
        dark: 'rgba(52, 58, 64, 0.8)',
        purple: 'rgba(153, 102, 255, 0.8)',
        orange: 'rgba(255, 159, 64, 0.8)',
        teal: 'rgba(32, 201, 151, 0.8)',
        indigo: 'rgba(102, 16, 242, 0.8)',
        chartText: getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim() || '#333',
        chartSecondaryText: getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim() || '#666',
        chartGrid: 'rgba(76, 80, 197, 0.08)',
        chartBorder: 'rgba(76, 80, 197, 0.2)',
        tooltipBackground: theme === 'dark' ? 'rgba(40, 44, 52, 0.9)' : 'rgba(255, 255, 255, 0.9)',
        tooltipText: theme === 'dark' ? '#e3e3e3' : '#333'
    };
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize dashboard
    initializeDashboard();

    // Refresh data every 5 minutes
    setInterval(loadDashboardData, 300000);
});

function initializeDashboard() {
    loadDashboardData();
    setupEventListeners();
}

function setupEventListeners() {
    // Add refresh button listener
    const refreshBtn = document.getElementById('refreshDashboard');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadDashboardData);
    }
}

function loadDashboardData() {
    console.log('Loading dashboard data...');
    showLoading(true);

    // Load main dashboard summary (now includes all organized data)
    Promise.allSettled([
        loadDashboardSummary(),
        loadInventoryStatus(), 
        loadFinancialSummary()
    ]).then(() => {
        showLoading(false);
        console.log('Dashboard data loaded successfully');
    }).catch(error => {
        console.error('Error loading dashboard:', error);
        showLoading(false);
        showError('Failed to load dashboard data');
    });
}

function updateInventoryMetrics(inventory) {
    // Update inventory summary cards
    updateElement('totalItems', inventory.total_items || 0);
    updateElement('totalStock', inventory.total_stock || 0);
    updateElement('inventoryValue', formatCurrency(inventory.inventory_value || 0));
    updateElement('lowStockCount', inventory.low_stock_count || 0);
    
    // Update low stock items list
    if (inventory.low_stock_items) {
        updateLowStockItems(inventory.low_stock_items);
    }
    
    // Update category breakdown
    if (inventory.category_breakdown) {
        updateCategoryBreakdown(inventory.category_breakdown);
    }
}

function updateSalesMetrics(sales) {
    // Update sales summary cards
    updateElement('totalSales', sales.total_sales || 0);
    updateElement('totalRevenue', formatCurrency(sales.total_revenue || 0));
    updateElement('todaySales', formatCurrency(sales.today_sales || 0));
    updateElement('todaySalesCount', sales.today_sales_count || 0);
    
    // Update top selling items
    if (sales.top_selling_items) {
        updateTopSellingItems(sales.top_selling_items);
    }
}

function updateCustomerMetrics(customers) {
    // Update customer summary cards
    updateElement('totalCustomers', customers.total_customers || 0);
    updateElement('newCustomersThisMonth', customers.new_customers_this_month || 0);
}

function updateFinancialMetrics(financial) {
    // Update financial summary cards
    updateElement('monthlyIncome', formatCurrency(financial.monthly_income || 0));
    updateElement('monthlyExpenses', formatCurrency(financial.monthly_expenses || 0));
    updateElement('monthlyProfit', formatCurrency(financial.monthly_profit || 0));
    
    // Add visual indicator for profit/loss
    const profitElement = document.getElementById('monthlyProfit');
    if (profitElement) {
        const profit = financial.monthly_profit || 0;
        profitElement.className = profit >= 0 ? 'text-success' : 'text-danger';
    }
}

function updateRecentActivity(activity) {
    if (activity.recent_sales) {
        updateRecentSales(activity.recent_sales);
    }
}

function updateCategoryBreakdown(categories) {
    const container = document.getElementById('categoryBreakdown');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (categories.length === 0) {
        container.innerHTML = '<p class="text-muted">No categories found</p>';
        return;
    }
    
    categories.forEach(category => {
        const categoryElement = document.createElement('div');
        categoryElement.className = 'mb-2 p-2 border rounded';
        categoryElement.innerHTML = `
            <div class="d-flex justify-content-between">
                <span class="fw-bold">${category.category}</span>
                <span class="badge bg-primary">${category.item_count} items</span>
            </div>
            <small class="text-muted">Stock: ${category.total_stock}</small>
        `;
        container.appendChild(categoryElement);
    });
}

function updateTopSellingItems(items) {
    const container = document.getElementById('topSellingItems');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (items.length === 0) {
        container.innerHTML = '<p class="text-muted">No sales data available</p>';
        return;
    }
    
    items.forEach((item, index) => {
        const itemElement = document.createElement('div');
        itemElement.className = 'mb-2 p-2 border rounded';
        itemElement.innerHTML = `
            <div class="d-flex justify-content-between">
                <span>${index + 1}. ${item.name}</span>
                <span class="badge bg-success">${item.quantity_sold} sold</span>
            </div>
        `;
        container.appendChild(itemElement);
    });
}

function loadDashboardSummary() {
    return fetch('/api/dashboard/summary', {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Update dashboard with organized data
            updateInventoryMetrics(data.inventory);
            updateSalesMetrics(data.sales);
            updateCustomerMetrics(data.customers);
            updateFinancialMetrics(data.financial);
            updateRecentActivity(data.recent_activity);
        } else {
            throw new Error(data.error || 'Failed to load dashboard summary');
        }
    })
    .catch(error => {
        console.error('Error loading dashboard summary:', error);
        // Set default values to prevent UI breakage
        updateInventoryMetrics({
            total_items: 0,
            total_stock: 0,
            low_stock_count: 0,
            inventory_value: 0,
            category_breakdown: []
        });
        updateSalesMetrics({
            total_sales: 0,
            total_revenue: 0,
            today_sales: 0,
            today_sales_count: 0,
            top_selling_items: []
        });
        updateCustomerMetrics({
            total_customers: 0,
            new_customers_this_month: 0
        });
        updateFinancialMetrics({
            monthly_income: 0,
            monthly_expenses: 0,
            monthly_profit: 0
        });
    });
}

function loadInventoryStatus() {
    return fetch('/api/inventory?limit=5', {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(items => {
        updateInventoryStatus(Array.isArray(items) ? items : []);
    })
    .catch(error => {
        console.error('Error loading inventory status:', error);
        updateInventoryStatus([]);
    });
}

function loadRecentSales() {
    return fetch('/api/sales?per_page=5', {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success && data.sales) {
            updateRecentSales(data.sales);
        } else {
            updateRecentSales([]);
        }
    })
    .catch(error => {
        console.error('Error loading recent sales:', error);
        updateRecentSales([]);
    });
}

function loadFinancialSummary() {
    return fetch('/api/finance/summaries/monthly', {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        updateFinancialSummary(data);
    })
    .catch(error => {
        console.error('Error loading financial summary:', error);
        updateFinancialSummary({ monthly_data: [] });
    });
}

function loadLowStockItems() {
    return fetch('/api/reports/stock-status', {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        updateLowStockItems(data.low_stock_items || []);
    })
    .catch(error => {
        console.error('Error loading low stock items:', error);
        updateLowStockItems([]);
    });
}

function loadTopSellingItems() {
    return fetch('/api/sales', {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        // Calculate top selling items from sales data
        const itemSales = {};
        if (data && Array.isArray(data)) {
            data.forEach(sale => {
                if (sale.sale_items) {
                    sale.sale_items.forEach(item => {
                        const itemName = item.item_name || item.name;
                        if (itemSales[itemName]) {
                            itemSales[itemName] += item.quantity;
                        } else {
                            itemSales[itemName] = item.quantity;
                        }
                    });
                }
            });
        }
        
        // Convert to array and sort by sales quantity
        const topItems = Object.entries(itemSales)
            .map(([name, quantity]) => ({ name, quantity }))
            .sort((a, b) => b.quantity - a.quantity)
            .slice(0, 5);
            
        updateTopSellingItems(topItems);
    })
    .catch(error => {
        console.error('Error loading top selling items:', error);
        updateTopSellingItems([]);
    });
}

// Update functions
function updateDashboardSummary(summary) {
    const elements = {
        'total-items': summary.total_items || 0,
        'total-stock': summary.total_stock || 0,
        'low-stock-count': summary.low_stock_count || 0,
        'inventory-value': formatCurrency(summary.inventory_value || 0),
        'total-customers': summary.total_customers || 0,
        'monthly-income': formatCurrency(summary.monthly_income || 0),
        'monthly-expenses': formatCurrency(summary.monthly_expenses || 0),
        'monthly-profit': formatCurrency(summary.monthly_profit || 0)
    };

    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });

    // Update profit color
    const profitElement = document.getElementById('monthly-profit');
    if (profitElement && summary.monthly_profit !== undefined) {
        profitElement.className = summary.monthly_profit >= 0 ? 'text-success' : 'text-danger';
    }
}

function updateInventoryStatus(items) {
    const container = document.getElementById('inventory-status');
    if (!container) return;

    if (items.length === 0) {
        container.innerHTML = '<p class="text-muted">No inventory items found.</p>';
        return;
    }

    let html = '<div class="row">';
    items.slice(0, 5).forEach(item => {
        const stockLevel = (item.stock_quantity || 0) <= (item.minimum_stock || 0) ? 'danger' : 'success';
        html += `
            <div class="col-md-12 mb-2">
                <div class="d-flex justify-content-between align-items-center">
                    <span>${item.name}</span>
                    <span class="badge bg-${stockLevel}">${item.stock_quantity || 0}</span>
                </div>
            </div>
        `;
    });
    html += '</div>';
    container.innerHTML = html;
}

function updateRecentSales(sales) {
    const container = document.getElementById('recent-sales');
    if (!container) return;

    if (sales.length === 0) {
        container.innerHTML = '<p class="text-muted">No recent sales found.</p>';
        return;
    }

    let html = '<div class="list-group">';
    sales.slice(0, 5).forEach(sale => {
        html += `
            <div class="list-group-item">
                <div class="d-flex justify-content-between">
                    <span>#${sale.sale_number || sale.id}</span>
                    <span class="fw-bold">${formatCurrency(sale.total_amount || 0)}</span>
                </div>
                <small class="text-muted">${sale.customer_name || 'Walk-in Customer'}</small>
            </div>
        `;
    });
    html += '</div>';
    container.innerHTML = html;
}

function updateFinancialSummary(data) {
    const container = document.getElementById('financial-summary');
    if (!container) return;

    if (!data.monthly_data || data.monthly_data.length === 0) {
        container.innerHTML = '<p class="text-muted">No financial data available.</p>';
        return;
    }

    // Simple summary for current month
    const currentMonth = data.monthly_data[new Date().getMonth()] || {};
    const html = `
        <div class="row">
            <div class="col-6">
                <h6>Income</h6>
                <p class="text-success">${formatCurrency(currentMonth.income || 0)}</p>
            </div>
            <div class="col-6">
                <h6>Expenses</h6>
                <p class="text-danger">${formatCurrency(currentMonth.expenses || 0)}</p>
            </div>
        </div>
    `;
    container.innerHTML = html;
}

function updateLowStockItems(items) {
    const container = document.getElementById('low-stock-items');
    if (!container) return;

    if (items.length === 0) {
        container.innerHTML = '<p class="text-muted">No low stock items.</p>';
        return;
    }

    let html = '<div class="list-group">';
    items.slice(0, 5).forEach(item => {
        html += `
            <div class="list-group-item d-flex justify-content-between align-items-center">
                <span>${item.name}</span>
                <span class="badge bg-warning">${item.stock_quantity || 0} / ${item.minimum_stock || 0}</span>
            </div>
        `;
    });
    html += '</div>';
    container.innerHTML = html;
}

function updateTopSellingItems(items) {
    const container = document.getElementById('top-selling-items');
    if (!container) return;

    if (items.length === 0) {
        container.innerHTML = '<p class="text-muted">No sales data available.</p>';
        return;
    }

    let html = '<div class="list-group">';
    items.slice(0, 5).forEach(item => {
        html += `
            <div class="list-group-item d-flex justify-content-between align-items-center">
                <span>${item.name}</span>
                <span class="badge bg-primary">${item.units_sold || 0} sold</span>
            </div>
        `;
    });
    html += '</div>';
    container.innerHTML = html;
}

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-TZ', {
        style: 'currency',
        currency: 'TZS',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount || 0);
}

function updateElement(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
    }
}

function showLoading(show) {
    const loader = document.getElementById('dashboard-loader');
    if (loader) {
        loader.style.display = show ? 'block' : 'none';
    }
}

function showError(message) {
    const alertContainer = document.getElementById('alert-container');
    if (alertContainer) {
        alertContainer.innerHTML = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
    } else {
        console.error('Error:', message);
    }
}

// Initialize translations
const savedLanguage = localStorage.getItem('preferred_language') || 'en';
updatePageLanguage(savedLanguage);

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

function updatePageLanguage(lang) {
    // Implement your translation logic here
}

function loadShopDetails() {
    // Fetch shop details from the API
    fetch('/api/shop/details')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const user = data.user;

                // Update DOM elements
                const shopNameElement = document.getElementById('shop-name');
                if (shopNameElement) {
                    shopNameElement.textContent = user.shop_name || 'Your Shop';
                }
            }
        })
        .catch(error => {
            console.error('Error loading shop details:', error);
            // Fallback to a default name
            const shopNameElement = document.getElementById('shop-name');
            if (shopNameElement) {
                shopNameElement.textContent = "Your Shop";
            }
        });
}

// Initialize
loadShopDetails();