document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const reportTypeSelect = document.getElementById('reportType');
    const lowStockThresholdInput = document.getElementById('lowStockThreshold');
    const generateReportBtn = document.getElementById('generateReportBtn');
    
    // Report Section Elements
    const stockStatusReport = document.getElementById('stockStatusReport');
    const categoryBreakdownReport = document.getElementById('categoryBreakdownReport');
    const valueAnalysisReport = document.getElementById('valueAnalysisReport');
    
    // Charts
    let categoryItemsChart = null;
    let categoryStockChart = null;
    let categoryValueChart = null;
    
    // Load initial report
    generateReport();
    
    // Event Listeners
    generateReportBtn.addEventListener('click', generateReport);
    reportTypeSelect.addEventListener('change', function() {
        // Update visibility of threshold input based on report type
        if (this.value === 'stock-status') {
            document.querySelector('label[for="lowStockThreshold"]').classList.remove('d-none');
            lowStockThresholdInput.classList.remove('d-none');
        } else {
            document.querySelector('label[for="lowStockThreshold"]').classList.add('d-none');
            lowStockThresholdInput.classList.add('d-none');
        }
    });
    
    function generateReport() {
        const reportType = reportTypeSelect.value;
        
        // Hide all report sections
        stockStatusReport.classList.add('d-none');
        categoryBreakdownReport.classList.add('d-none');
        valueAnalysisReport.classList.add('d-none');
        
        // Show selected report section
        if (reportType === 'stock-status') {
            stockStatusReport.classList.remove('d-none');
            generateStockStatusReport();
        } else if (reportType === 'category-breakdown') {
            categoryBreakdownReport.classList.remove('d-none');
            generateCategoryBreakdownReport();
        } else if (reportType === 'value-analysis') {
            valueAnalysisReport.classList.remove('d-none');
            generateValueAnalysisReport();
        }
    }
    
    function generateStockStatusReport() {
        const lowStockThreshold = parseInt(lowStockThresholdInput.value) || 10;
        
        fetch(`/api/reports/stock-status?low_stock_threshold=${lowStockThreshold}`)
            .then(response => response.json())
            .then(data => {
                updateStockStatusSummary(data);
                updateLowStockTable(data.low_stock_items);
            })
            .catch(error => {
                console.error('Error generating stock status report:', error);
            });
    }
    
    function generateCategoryBreakdownReport() {
        fetch('/api/reports/category-breakdown')
            .then(response => response.json())
            .then(data => {
                createCategoryItemsChart(data);
                createCategoryStockChart(data);
                updateCategoryBreakdownTable(data);
            })
            .catch(error => {
                console.error('Error generating category breakdown report:', error);
            });
    }
    
    function generateValueAnalysisReport() {
        // Load category breakdown and inventory data for value analysis
        Promise.all([
            fetch('/api/reports/category-breakdown').then(res => res.json()),
            fetch('/api/inventory').then(res => res.json())
        ])
        .then(([categoryData, inventoryData]) => {
            createCategoryValueChart(categoryData);
            updateValueAnalysisSummary(categoryData, inventoryData);
            updateValueAnalysisTable(inventoryData);
        })
        .catch(error => {
            console.error('Error generating value analysis report:', error);
        });
    }
    
    function updateStockStatusSummary(data) {
        // Update summary cards
        document.getElementById('total-items').textContent = data.total_items;
        document.getElementById('total-stock').textContent = data.total_stock;
        document.getElementById('low-stock-count').textContent = data.low_stock_items_count;
        document.getElementById('out-of-stock-count').textContent = data.out_of_stock_items_count;
    }
    
    function updateLowStockTable(lowStockItems) {
        const lowStockTable = document.getElementById('low-stock-table');
        
        if (lowStockItems && lowStockItems.length > 0) {
            let tableHtml = '';
            
            // Sort by quantity (lowest first)
            lowStockItems.sort((a, b) => a.quantity - b.quantity);
            
            lowStockItems.forEach(item => {
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
            
            lowStockTable.innerHTML = tableHtml;
        } else {
            lowStockTable.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center">No low stock items found</td>
                </tr>
            `;
        }
    }
    
    function createCategoryItemsChart(categoryData) {
        // Prepare data for chart
        const categories = Object.keys(categoryData);
        const itemCounts = categories.map(category => categoryData[category].count);
        
        // Get canvas context
        const ctx = document.getElementById('categoryItemsChart').getContext('2d');
        
        // Destroy existing chart if it exists
        if (categoryItemsChart) {
            categoryItemsChart.destroy();
        }
        
        // Create new chart
        categoryItemsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: categories,
                datasets: [{
                    label: 'Number of Items',
                    data: itemCounts,
                    backgroundColor: 'rgba(75, 192, 192, 0.7)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Items'
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
    
    function createCategoryStockChart(categoryData) {
        // Prepare data for chart
        const categories = Object.keys(categoryData);
        const stockQuantities = categories.map(category => categoryData[category].total_quantity);
        
        // Get canvas context
        const ctx = document.getElementById('categoryStockChart').getContext('2d');
        
        // Destroy existing chart if it exists
        if (categoryStockChart) {
            categoryStockChart.destroy();
        }
        
        // Create new chart
        categoryStockChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: categories,
                datasets: [{
                    label: 'Total Stock',
                    data: stockQuantities,
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
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Total Stock Quantity'
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
    
    function updateCategoryBreakdownTable(categoryData) {
        const categoryBreakdownTable = document.getElementById('category-breakdown-table');
        
        if (Object.keys(categoryData).length > 0) {
            let tableHtml = '';
            
            // Sort categories by item count (highest first)
            const sortedCategories = Object.keys(categoryData).sort((a, b) => {
                return categoryData[b].count - categoryData[a].count;
            });
            
            sortedCategories.forEach(category => {
                const data = categoryData[category];
                const avgQuantity = (data.total_quantity / data.count).toFixed(1);
                
                tableHtml += `
                <tr>
                    <td>${category}</td>
                    <td>${data.count}</td>
                    <td>${data.total_quantity}</td>
                    <td>${avgQuantity}</td>
                    <td><span class="currency-symbol">TZS</span> ${data.total_value.toLocaleString()}</td>
                </tr>
                `;
            });
            
            categoryBreakdownTable.innerHTML = tableHtml;
        } else {
            categoryBreakdownTable.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center">No categories found</td>
                </tr>
            `;
        }
    }
    
    function createCategoryValueChart(categoryData) {
        // Prepare data for chart
        const categories = Object.keys(categoryData);
        const values = categories.map(category => categoryData[category].total_value);
        
        // Get canvas context
        const ctx = document.getElementById('categoryValueChart').getContext('2d');
        
        // Destroy existing chart if it exists
        if (categoryValueChart) {
            categoryValueChart.destroy();
        }
        
        // Create new chart
        categoryValueChart = new Chart(ctx, {
            type: 'pie',
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
                                return `${label}: $${value.toFixed(2)} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    function updateValueAnalysisSummary(categoryData, inventoryData) {
        // Calculate total inventory value
        const totalValue = Object.values(categoryData).reduce(
            (sum, category) => sum + category.total_value, 0
        );
        
        // Calculate average item value
        const avgItemValue = totalValue / inventoryData.length;
        
        // Find highest value category
        let highestValueCategory = '';
        let highestCategoryValue = 0;
        
        for (const category in categoryData) {
            if (categoryData[category].total_value > highestCategoryValue) {
                highestValueCategory = category;
                highestCategoryValue = categoryData[category].total_value;
            }
        }
        
        // Find highest value item
        let highestValueItem = { name: 'None' };
        let highestItemTotalValue = 0;
        
        inventoryData.forEach(item => {
            const itemTotalValue = item.quantity * item.price;
            if (itemTotalValue > highestItemTotalValue) {
                highestValueItem = item;
                highestItemTotalValue = itemTotalValue;
            }
        });
        
        // Update summary elements
        document.getElementById('total-inventory-value').innerHTML = `<span class="currency-symbol">TZS</span> ${totalValue.toLocaleString()}`;
        document.getElementById('average-item-value').innerHTML = `<span class="currency-symbol">TZS</span> ${avgItemValue.toLocaleString()}`;
        document.getElementById('highest-value-category').textContent = highestValueCategory;
        document.getElementById('highest-value-item').textContent = highestValueItem.name;
    }
    
    function updateValueAnalysisTable(inventoryData) {
        const valueAnalysisTable = document.getElementById('value-analysis-table');
        
        if (inventoryData && inventoryData.length > 0) {
            // Calculate total value for each item
            inventoryData.forEach(item => {
                item.total_value = item.quantity * item.price;
            });
            
            // Sort by total value (highest first)
            inventoryData.sort((a, b) => b.total_value - a.total_value);
            
            let tableHtml = '';
            
            inventoryData.forEach(item => {
                tableHtml += `
                <tr>
                    <td>
                        <a href="/item/${item.id}" class="text-decoration-none">
                            ${item.name}
                        </a>
                    </td>
                    <td>${item.category || 'Uncategorized'}</td>
                    <td>${item.quantity}</td>
                    <td><span class="currency-symbol">TZS</span> ${item.price.toLocaleString()}</td>
                    <td><span class="currency-symbol">TZS</span> ${item.total_value.toLocaleString()}</td>
                </tr>
                `;
            });
            
            valueAnalysisTable.innerHTML = tableHtml;
        } else {
            valueAnalysisTable.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center">No items found</td>
                </tr>
            `;
        }
    }
});
