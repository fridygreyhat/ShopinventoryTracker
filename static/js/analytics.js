
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const refreshBtn = document.getElementById('refresh-analytics');
    const recommendationCount = document.getElementById('recommendation-count');
    const recommendationsTable = document.getElementById('recommendations-table');
    const marginTableHeader = document.getElementById('margin-table-header');
    const marginTableBody = document.getElementById('margin-table-body');
    const turnoverTable = document.getElementById('turnover-table');
    const turnoverPeriod = document.getElementById('turnover-period');
    const viewByProduct = document.getElementById('view-by-product');
    const viewByCategory = document.getElementById('view-by-category');

    // Charts
    let abcChart = null;

    // Current view state
    let currentMarginView = 'products';

    // Load initial data
    loadPurchaseRecommendations();
    loadABCAnalysis();
    loadProfitMarginAnalysis();
    loadInventoryTurnover();

    // Event listeners
    refreshBtn.addEventListener('click', function() {
        loadPurchaseRecommendations();
        loadABCAnalysis();
        loadProfitMarginAnalysis();
        loadInventoryTurnover();
    });

    viewByProduct.addEventListener('click', function() {
        currentMarginView = 'products';
        updateMarginViewButtons();
        loadProfitMarginAnalysis();
    });

    viewByCategory.addEventListener('click', function() {
        currentMarginView = 'categories';
        updateMarginViewButtons();
        loadProfitMarginAnalysis();
    });

    turnoverPeriod.addEventListener('change', function() {
        loadInventoryTurnover();
    });

    function updateMarginViewButtons() {
        viewByProduct.classList.toggle('active', currentMarginView === 'products');
        viewByCategory.classList.toggle('active', currentMarginView === 'categories');
    }

    function loadPurchaseRecommendations() {
        showLoading('recommendations');
        
        fetch('/api/analytics/purchase-recommendations')
            .then(response => response.json())
            .then(data => {
                hideLoading('recommendations');
                
                if (data.success && data.recommendations.length > 0) {
                    displayPurchaseRecommendations(data.recommendations);
                    recommendationCount.textContent = data.recommendations.length;
                    showContent('recommendations');
                } else {
                    showEmpty('recommendations');
                    recommendationCount.textContent = '0';
                }
            })
            .catch(error => {
                console.error('Error loading purchase recommendations:', error);
                hideLoading('recommendations');
                showError('recommendations', 'Failed to load purchase recommendations');
            });
    }

    function displayPurchaseRecommendations(recommendations) {
        let html = '';
        
        recommendations.forEach(rec => {
            const priorityClass = rec.priority === 'high' ? 'danger' : 'warning';
            const priorityIcon = rec.priority === 'high' ? 'exclamation-triangle' : 'info-circle';
            
            html += `
                <tr>
                    <td>
                        <strong>${rec.item_name}</strong>
                        <br><small class="text-muted">ID: ${rec.item_id}</small>
                    </td>
                    <td>
                        <span class="badge ${rec.current_stock === 0 ? 'bg-danger' : 'bg-secondary'}">
                            ${rec.current_stock}
                        </span>
                    </td>
                    <td>${rec.suggested_quantity}</td>
                    <td>
                        <span class="badge bg-${priorityClass}">
                            <i class="fas fa-${priorityIcon}"></i> ${rec.priority}
                        </span>
                    </td>
                    <td>
                        <span class="currency-symbol">TZS</span> ${rec.estimated_cost.toLocaleString()}
                    </td>
                </tr>
            `;
        });
        
        recommendationsTable.innerHTML = html;
    }

    function loadABCAnalysis() {
        showLoading('abc');
        
        fetch('/api/analytics/abc-analysis')
            .then(response => response.json())
            .then(data => {
                hideLoading('abc');
                
                if (data.error) {
                    showError('abc', data.error);
                    return;
                }
                
                displayABCAnalysis(data);
                showContent('abc');
            })
            .catch(error => {
                console.error('Error loading ABC analysis:', error);
                hideLoading('abc');
                showError('abc', 'Failed to load ABC analysis');
            });
    }

    function displayABCAnalysis(data) {
        // Update counts
        document.getElementById('class-a-count').textContent = data.summary.A_count || 0;
        document.getElementById('class-b-count').textContent = data.summary.B_count || 0;
        document.getElementById('class-c-count').textContent = data.summary.C_count || 0;

        // Create ABC chart
        createABCChart(data.summary);
    }

    function createABCChart(summary) {
        const ctx = document.getElementById('abc-chart').getContext('2d');
        
        if (abcChart) {
            abcChart.destroy();
        }
        
        abcChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Class A (High Value)', 'Class B (Medium Value)', 'Class C (Low Value)'],
                datasets: [{
                    data: [summary.A_count || 0, summary.B_count || 0, summary.C_count || 0],
                    backgroundColor: [
                        'rgba(0, 123, 255, 0.8)',
                        'rgba(255, 193, 7, 0.8)',
                        'rgba(108, 117, 125, 0.8)'
                    ],
                    borderColor: [
                        'rgba(0, 123, 255, 1)',
                        'rgba(255, 193, 7, 1)',
                        'rgba(108, 117, 125, 1)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    function loadProfitMarginAnalysis() {
        showLoading('margin');
        
        fetch('/api/reports/profit-margin')
            .then(response => response.json())
            .then(data => {
                hideLoading('margin');
                
                if (data.success) {
                    displayProfitMarginAnalysis(data);
                    showContent('margin');
                } else {
                    showError('margin', 'Failed to load profit margin data');
                }
            })
            .catch(error => {
                console.error('Error loading profit margin analysis:', error);
                hideLoading('margin');
                showError('margin', 'Failed to load profit margin analysis');
            });
    }

    function displayProfitMarginAnalysis(data) {
        if (currentMarginView === 'products') {
            displayProductMargins(data.item_margins);
        } else {
            displayCategoryMargins(data.category_margins);
        }
    }

    function displayProductMargins(items) {
        marginTableHeader.innerHTML = `
            <tr>
                <th>Product</th>
                <th>Category</th>
                <th>Buying Price</th>
                <th>Selling Price</th>
                <th>Margin %</th>
                <th>Units Sold</th>
                <th>Total Profit</th>
            </tr>
        `;

        let html = '';
        items.forEach(item => {
            const marginClass = item.margin_percentage >= 30 ? 'success' : 
                              item.margin_percentage >= 15 ? 'warning' : 'danger';
            
            html += `
                <tr>
                    <td><strong>${item.item_name}</strong></td>
                    <td>${item.category || 'Uncategorized'}</td>
                    <td><span class="currency-symbol">TZS</span> ${item.buying_price.toLocaleString()}</td>
                    <td><span class="currency-symbol">TZS</span> ${item.selling_price.toLocaleString()}</td>
                    <td>
                        <span class="badge bg-${marginClass}">
                            ${item.margin_percentage.toFixed(1)}%
                        </span>
                    </td>
                    <td>${item.units_sold}</td>
                    <td>
                        <span class="currency-symbol">TZS</span> 
                        <span class="${item.total_profit >= 0 ? 'text-success' : 'text-danger'}">
                            ${item.total_profit.toLocaleString()}
                        </span>
                    </td>
                </tr>
            `;
        });
        
        marginTableBody.innerHTML = html;
    }

    function displayCategoryMargins(categories) {
        marginTableHeader.innerHTML = `
            <tr>
                <th>Category</th>
                <th>Items Count</th>
                <th>Total Revenue</th>
                <th>Total Cost</th>
                <th>Total Profit</th>
                <th>Margin %</th>
            </tr>
        `;

        let html = '';
        Object.entries(categories).forEach(([categoryName, data]) => {
            const marginClass = data.margin_percentage >= 30 ? 'success' : 
                              data.margin_percentage >= 15 ? 'warning' : 'danger';
            
            html += `
                <tr>
                    <td><strong>${categoryName}</strong></td>
                    <td>${data.item_count}</td>
                    <td><span class="currency-symbol">TZS</span> ${data.total_revenue.toLocaleString()}</td>
                    <td><span class="currency-symbol">TZS</span> ${data.total_cost.toLocaleString()}</td>
                    <td>
                        <span class="currency-symbol">TZS</span> 
                        <span class="${data.total_profit >= 0 ? 'text-success' : 'text-danger'}">
                            ${data.total_profit.toLocaleString()}
                        </span>
                    </td>
                    <td>
                        <span class="badge bg-${marginClass}">
                            ${data.margin_percentage.toFixed(1)}%
                        </span>
                    </td>
                </tr>
            `;
        });
        
        marginTableBody.innerHTML = html;
    }

    function loadInventoryTurnover() {
        showLoading('turnover');
        
        const days = turnoverPeriod.value;
        
        fetch(`/api/reports/inventory-turnover?days=${days}`)
            .then(response => response.json())
            .then(data => {
                hideLoading('turnover');
                
                if (data.success) {
                    displayInventoryTurnover(data.turnover_analysis);
                    showContent('turnover');
                } else {
                    showError('turnover', 'Failed to load inventory turnover data');
                }
            })
            .catch(error => {
                console.error('Error loading inventory turnover:', error);
                hideLoading('turnover');
                showError('turnover', 'Failed to load inventory turnover');
            });
    }

    function displayInventoryTurnover(turnoverData) {
        let html = '';
        
        turnoverData.forEach(item => {
            const speedClass = {
                'Fast': 'success',
                'Medium': 'warning',
                'Slow': 'danger',
                'Very Slow': 'dark'
            }[item.turnover_speed] || 'secondary';
            
            html += `
                <tr>
                    <td><strong>${item.item_name}</strong></td>
                    <td>${item.category || 'Uncategorized'}</td>
                    <td>${item.current_inventory}</td>
                    <td>${item.units_sold}</td>
                    <td>${item.turnover_ratio}</td>
                    <td>${item.days_of_inventory}</td>
                    <td>
                        <span class="badge bg-${speedClass}">
                            ${item.turnover_speed}
                        </span>
                    </td>
                    <td><span class="currency-symbol">TZS</span> ${item.inventory_value.toLocaleString()}</td>
                </tr>
            `;
        });
        
        turnoverTable.innerHTML = html;
    }

    // Utility functions
    function showLoading(section) {
        document.getElementById(`${section}-loading`).classList.remove('d-none');
        document.getElementById(`${section}-content`).classList.add('d-none');
        document.getElementById(`${section}-empty`).classList.add('d-none');
    }

    function hideLoading(section) {
        document.getElementById(`${section}-loading`).classList.add('d-none');
    }

    function showContent(section) {
        document.getElementById(`${section}-content`).classList.remove('d-none');
    }

    function showEmpty(section) {
        document.getElementById(`${section}-empty`).classList.remove('d-none');
    }

    function showError(section, message) {
        const contentElement = document.getElementById(`${section}-content`);
        contentElement.innerHTML = `
            <div class="alert alert-danger" role="alert">
                <i class="fas fa-exclamation-triangle"></i> ${message}
            </div>
        `;
        contentElement.classList.remove('d-none');
    }

    // Initialize margin view buttons
    updateMarginViewButtons();
});
</script>
