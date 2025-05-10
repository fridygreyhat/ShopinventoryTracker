document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const totalItemsElement = document.getElementById('total-items');
    const totalStockElement = document.getElementById('total-stock');
    const lowStockCountElement = document.getElementById('low-stock-count');
    const inventoryValueElement = document.getElementById('inventory-value');
    const lowStockTableElement = document.getElementById('low-stock-table');
    
    // Charts
    let stockChart = null;
    let valueChart = null;
    
    // Load dashboard data
    loadDashboardData();
    
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
                    <td><span class="badge ${quantityClass}">${item.quantity}</span></td>
                    <td><span class="currency-symbol">TZS</span> ${item.price.toLocaleString()}</td>
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
                    backgroundColor: 'rgba(54, 162, 235, 0.7)',
                    borderColor: 'rgba(54, 162, 235, 1)',
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
                        title: {
                            display: true,
                            text: 'Quantity'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Category'
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
                        'rgba(255, 99, 132, 0.7)',
                        'rgba(54, 162, 235, 0.7)',
                        'rgba(255, 206, 86, 0.7)',
                        'rgba(75, 192, 192, 0.7)',
                        'rgba(153, 102, 255, 0.7)',
                        'rgba(255, 159, 64, 0.7)',
                        'rgba(199, 199, 199, 0.7)',
                        'rgba(83, 102, 255, 0.7)',
                        'rgba(40, 159, 64, 0.7)',
                        'rgba(210, 199, 199, 0.7)'
                    ],
                    borderColor: [
                        'rgba(255, 99, 132, 1)',
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 206, 86, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(153, 102, 255, 1)',
                        'rgba(255, 159, 64, 1)',
                        'rgba(199, 199, 199, 1)',
                        'rgba(83, 102, 255, 1)',
                        'rgba(40, 159, 64, 1)',
                        'rgba(210, 199, 199, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw;
                                const label = context.label || '';
                                const percentage = ((value / values.reduce((a, b) => a + b, 0)) * 100).toFixed(1);
                                return `${label}: <span class="currency-symbol">TZS</span> ${value.toLocaleString()} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
});
