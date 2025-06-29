
document.addEventListener('DOMContentLoaded', function() {
    // Chart instances
    let demandForecastChart = null;
    let seasonalTrendsChart = null;
    let customerSegmentsChart = null;
    let abcAnalysisChart = null;
    let healthScoreGauge = null;

    // Initialize dashboard
    initializeAnalyticsDashboard();

    // Event listeners
    document.getElementById('refreshAnalytics').addEventListener('click', refreshAllAnalytics);
    document.getElementById('forecast7Days').addEventListener('click', () => loadDemandForecast(7));
    document.getElementById('forecast30Days').addEventListener('click', () => loadDemandForecast(30));
    document.getElementById('forecast90Days').addEventListener('click', () => loadDemandForecast(90));
    document.getElementById('generateAutoOrders').addEventListener('click', generateAutoOrders);

    function initializeAnalyticsDashboard() {
        // Load all analytics components
        loadDemandForecast(30);
        loadSeasonalTrends();
        loadPriceOptimization();
        loadCustomerBehavior();
        loadABCAnalysis();
        loadInventoryHealthScore();
        loadAutoReorderSuggestions();
    }

    function loadDemandForecast(daysAhead = 30) {
        fetch(`/api/analytics/demand-forecast?days_ahead=${daysAhead}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateDemandForecastSummary(data);
                    createDemandForecastChart(data.forecasts);
                }
            })
            .catch(error => {
                console.error('Error loading demand forecast:', error);
            });
    }

    function loadSeasonalTrends() {
        fetch('/api/analytics/seasonal-trends')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    createSeasonalTrendsChart(data.seasonal_patterns);
                }
            })
            .catch(error => {
                console.error('Error loading seasonal trends:', error);
            });
    }

    function loadPriceOptimization() {
        fetch('/api/analytics/price-optimization')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updatePriceOptimizationTable(data.recommendations);
                    updatePricingOpportunitiesCount(data.recommendations);
                }
            })
            .catch(error => {
                console.error('Error loading price optimization:', error);
            });
    }

    function loadCustomerBehavior() {
        fetch('/api/analytics/customer-behavior')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    createCustomerSegmentsChart(data.customer_segments);
                    updateCustomerSegmentsCount(data.customer_segments);
                }
            })
            .catch(error => {
                console.error('Error loading customer behavior:', error);
            });
    }

    function loadABCAnalysis() {
        fetch('/api/smart-inventory/abc-analysis')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    createABCAnalysisChart(data.abc_analysis);
                    updateABCCounts(data.abc_analysis);
                }
            })
            .catch(error => {
                console.error('Error loading ABC analysis:', error);
            });
    }

    function loadInventoryHealthScore() {
        fetch('/api/smart-inventory/health-score')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    createHealthScoreGauge(data.health_score);
                    updateHealthRecommendations(data.recommendations);
                }
            })
            .catch(error => {
                console.error('Error loading health score:', error);
            });
    }

    function loadAutoReorderSuggestions() {
        fetch('/api/smart-inventory/auto-reorder')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateAutoReorderTable(data);
                }
            })
            .catch(error => {
                console.error('Error loading auto-reorder suggestions:', error);
            });
    }

    function updateDemandForecastSummary(data) {
        const totalForecast = data.forecasts.reduce((sum, item) => sum + item.forecast, 0);
        document.getElementById('totalDemandForecast').textContent = totalForecast.toLocaleString();
        
        // Calculate forecast accuracy (simplified)
        const highConfidenceItems = data.forecasts.filter(item => item.confidence === 'high').length;
        const accuracy = (highConfidenceItems / data.forecasts.length * 100).toFixed(0);
        document.getElementById('forecastAccuracy').textContent = accuracy + '%';
    }

    function createDemandForecastChart(forecasts) {
        const ctx = document.getElementById('demandForecastChart').getContext('2d');
        
        if (demandForecastChart) {
            demandForecastChart.destroy();
        }

        const labels = forecasts.map(item => item.name);
        const forecastData = forecasts.map(item => item.forecast);
        const currentData = forecasts.map(item => item.daily_average * 30); // Approximate current monthly

        demandForecastChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Current Trend',
                        data: currentData,
                        backgroundColor: 'rgba(54, 162, 235, 0.5)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Forecast',
                        data: forecastData,
                        backgroundColor: 'rgba(255, 99, 132, 0.5)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
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

    function createSeasonalTrendsChart(seasonalData) {
        const ctx = document.getElementById('seasonalTrendsChart').getContext('2d');
        
        if (seasonalTrendsChart) {
            seasonalTrendsChart.destroy();
        }

        // Process data for chart
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        
        // Get top 3 items for seasonal trends
        const topItems = seasonalData.slice(0, 3);
        const datasets = topItems.map((item, index) => {
            const colors = ['rgba(255, 99, 132, 0.8)', 'rgba(54, 162, 235, 0.8)', 'rgba(255, 205, 86, 0.8)'];
            
            const monthlyData = months.map((month, monthIndex) => {
                const monthData = item.monthly_data[monthIndex + 1];
                return monthData ? monthData.total_quantity : 0;
            });

            return {
                label: item.name,
                data: monthlyData,
                borderColor: colors[index],
                backgroundColor: colors[index].replace('0.8', '0.2'),
                borderWidth: 2,
                fill: false
            };
        });

        seasonalTrendsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: months,
                datasets: datasets
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

    function updatePriceOptimizationTable(recommendations) {
        const tableBody = document.getElementById('priceOptimizationTable');
        
        if (!recommendations || recommendations.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center">No price optimization opportunities found</td></tr>';
            return;
        }

        let html = '';
        recommendations.forEach(item => {
            if (item.recommendations && item.recommendations.length > 0) {
                item.recommendations.forEach(rec => {
                    const changePercent = ((rec.recommended_price - rec.current_price) / rec.current_price * 100).toFixed(1);
                    const changeClass = changePercent > 0 ? 'text-success' : 'text-danger';
                    const changeIcon = changePercent > 0 ? 'fa-arrow-up' : 'fa-arrow-down';

                    html += `
                        <tr>
                            <td>${item.name}</td>
                            <td><span class="currency-symbol">TZS</span> ${rec.current_price.toLocaleString()}</td>
                            <td>
                                <span class="currency-symbol">TZS</span> ${rec.recommended_price.toLocaleString()}
                                <small class="${changeClass}">
                                    <i class="fas ${changeIcon}"></i> ${Math.abs(changePercent)}%
                                </small>
                            </td>
                            <td><small>${rec.expected_impact}</small></td>
                            <td>
                                <button class="btn btn-sm btn-primary apply-price-btn" 
                                        data-item-id="${item.item_id}" 
                                        data-new-price="${rec.recommended_price}">
                                    <i class="fas fa-check"></i> Apply
                                </button>
                            </td>
                        </tr>
                    `;
                });
            }
        });

        tableBody.innerHTML = html;

        // Add event listeners to apply buttons
        document.querySelectorAll('.apply-price-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const itemId = this.dataset.itemId;
                const newPrice = this.dataset.newPrice;
                applyPriceOptimization(itemId, newPrice, this);
            });
        });
    }

    function createCustomerSegmentsChart(segments) {
        const ctx = document.getElementById('customerSegmentsChart').getContext('2d');
        
        if (customerSegmentsChart) {
            customerSegmentsChart.destroy();
        }

        const segmentCounts = {
            'High Value': segments.high_value?.length || 0,
            'Frequent Buyers': segments.frequent_buyers?.length || 0,
            'New Customers': segments.new_customers?.length || 0,
            'At Risk': segments.at_risk?.length || 0
        };

        customerSegmentsChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: Object.keys(segmentCounts),
                datasets: [{
                    data: Object.values(segmentCounts),
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 205, 86, 0.8)',
                        'rgba(75, 192, 192, 0.8)'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });

        // Update segment details
        updateCustomerSegmentDetails(segments);
    }

    function createABCAnalysisChart(abcData) {
        const ctx = document.getElementById('abcAnalysisChart').getContext('2d');
        
        if (abcAnalysisChart) {
            abcAnalysisChart.destroy();
        }

        const classificationCounts = {
            'A': abcData.filter(item => item.abc_classification === 'A').length,
            'B': abcData.filter(item => item.abc_classification === 'B').length,
            'C': abcData.filter(item => item.abc_classification === 'C').length
        };

        abcAnalysisChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Class A', 'Class B', 'Class C'],
                datasets: [{
                    data: Object.values(classificationCounts),
                    backgroundColor: [
                        'rgba(40, 167, 69, 0.8)',
                        'rgba(255, 193, 7, 0.8)',
                        'rgba(23, 162, 184, 0.8)'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    function createHealthScoreGauge(score) {
        const canvas = document.getElementById('healthScoreGauge');
        const ctx = canvas.getContext('2d');
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Draw gauge
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const radius = 80;
        
        // Background arc
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, Math.PI, 2 * Math.PI);
        ctx.lineWidth = 20;
        ctx.strokeStyle = '#e9ecef';
        ctx.stroke();
        
        // Score arc
        const scoreAngle = Math.PI + (score / 100) * Math.PI;
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, Math.PI, scoreAngle);
        ctx.lineWidth = 20;
        
        // Color based on score
        if (score >= 80) {
            ctx.strokeStyle = '#28a745';
        } else if (score >= 60) {
            ctx.strokeStyle = '#ffc107';
        } else {
            ctx.strokeStyle = '#dc3545';
        }
        ctx.stroke();
        
        // Update score text
        document.getElementById('healthScoreValue').textContent = score;
    }

    function updateAutoReorderTable(data) {
        const tableBody = document.getElementById('autoReorderTable');
        
        if (!data.manual_reviews || data.manual_reviews.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="7" class="text-center">No reorder suggestions at this time</td></tr>';
            return;
        }

        let html = '';
        data.manual_reviews.forEach(item => {
            const urgencyBadge = getUrgencyBadge(item.urgency_level);
            const stockoutText = item.days_until_stockout ? 
                `${item.days_until_stockout} days` : 'Unknown';

            html += `
                <tr>
                    <td>${item.name}</td>
                    <td>${item.current_stock}</td>
                    <td>${item.daily_sales_rate}</td>
                    <td>${stockoutText}</td>
                    <td>${item.suggested_quantity} units</td>
                    <td>${urgencyBadge}</td>
                    <td>
                        <button class="btn btn-sm btn-success create-order-btn" 
                                data-item-id="${item.item_id}"
                                data-quantity="${item.suggested_quantity}">
                            <i class="fas fa-plus"></i> Order
                        </button>
                    </td>
                </tr>
            `;
        });

        tableBody.innerHTML = html;
    }

    // Helper functions
    function updatePricingOpportunitiesCount(recommendations) {
        const opportunities = recommendations.reduce((count, item) => 
            count + (item.recommendations ? item.recommendations.length : 0), 0);
        document.getElementById('pricingOpportunities').textContent = opportunities;
    }

    function updateCustomerSegmentsCount(segments) {
        const totalSegments = Object.keys(segments).length;
        document.getElementById('customerSegments').textContent = totalSegments;
    }

    function updateABCCounts(abcData) {
        const classA = abcData.filter(item => item.abc_classification === 'A').length;
        const classB = abcData.filter(item => item.abc_classification === 'B').length;
        const classC = abcData.filter(item => item.abc_classification === 'C').length;
        
        document.getElementById('classACount').textContent = classA;
        document.getElementById('classBCount').textContent = classB;
        document.getElementById('classCCount').textContent = classC;
    }

    function updateHealthRecommendations(recommendations) {
        const container = document.getElementById('healthRecommendations');
        
        if (!recommendations || recommendations.length === 0) {
            container.innerHTML = '<p class="text-success">Your inventory health is good!</p>';
            return;
        }

        let html = '<h6>Recommendations:</h6><ul class="list-unstyled">';
        recommendations.forEach(rec => {
            html += `<li><i class="fas fa-info-circle text-primary me-2"></i>${rec}</li>`;
        });
        html += '</ul>';
        
        container.innerHTML = html;
    }

    function updateCustomerSegmentDetails(segments) {
        const container = document.getElementById('customerSegmentDetails');
        
        let html = '<div class="row text-center">';
        
        const segmentInfo = [
            { key: 'high_value', label: 'High Value', color: 'success' },
            { key: 'frequent_buyers', label: 'Frequent', color: 'primary' },
            { key: 'new_customers', label: 'New', color: 'warning' },
            { key: 'at_risk', label: 'At Risk', color: 'danger' }
        ];

        segmentInfo.forEach(seg => {
            const count = segments[seg.key]?.length || 0;
            html += `
                <div class="col-6 mb-2">
                    <span class="badge bg-${seg.color}">${count}</span>
                    <small class="d-block">${seg.label}</small>
                </div>
            `;
        });

        html += '</div>';
        container.innerHTML = html;
    }

    function getUrgencyBadge(urgencyLevel) {
        const badges = {
            'critical': '<span class="badge bg-danger">Critical</span>',
            'high': '<span class="badge bg-warning">High</span>',
            'medium': '<span class="badge bg-info">Medium</span>',
            'low': '<span class="badge bg-secondary">Low</span>'
        };
        return badges[urgencyLevel] || badges['low'];
    }

    function applyPriceOptimization(itemId, newPrice, buttonElement) {
        // Simulate API call to update price
        fetch(`/api/inventory/${itemId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                selling_price_retail: parseFloat(newPrice)
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success || data.id) {
                buttonElement.innerHTML = '<i class="fas fa-check text-success"></i> Applied';
                buttonElement.disabled = true;
                buttonElement.classList.remove('btn-primary');
                buttonElement.classList.add('btn-outline-success');
            }
        })
        .catch(error => {
            console.error('Error applying price optimization:', error);
            alert('Failed to apply price optimization');
        });
    }

    function generateAutoOrders() {
        fetch('/api/smart-inventory/auto-reorder?supplier_integration=true', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(`Generated ${data.auto_orders_created} automatic orders`);
                loadAutoReorderSuggestions(); // Refresh the table
            }
        })
        .catch(error => {
            console.error('Error generating auto orders:', error);
        });
    }

    function refreshAllAnalytics() {
        document.getElementById('refreshAnalytics').innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
        
        // Reload all components
        initializeAnalyticsDashboard();
        
        setTimeout(() => {
            document.getElementById('refreshAnalytics').innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
        }, 2000);
    }
});
