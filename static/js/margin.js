// Helper function to get current theme colors
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
        chartText: getComputedStyle(document.documentElement).getPropertyValue('--bs-body-color').trim() || '#333',
        chartSecondaryText: getComputedStyle(document.documentElement).getPropertyValue('--bs-secondary-color').trim() || '#666',
        chartGrid: 'rgba(76, 80, 197, 0.08)',
        chartBorder: 'rgba(76, 80, 197, 0.2)',
        tooltipBackground: getComputedStyle(document.documentElement).getPropertyValue('--bs-card-bg').trim() || 'rgba(255, 255, 255, 0.9)',
        tooltipText: getComputedStyle(document.documentElement).getPropertyValue('--bs-body-color').trim() || '#333'
    };
}

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const categoryFilterElement = document.getElementById('category-filter');
    const searchFilterElement = document.getElementById('search-filter');
    const applyFiltersButton = document.getElementById('apply-filters-btn');
    const resetFiltersButton = document.getElementById('reset-filters-btn');
    const marginTableElement = document.getElementById('margin-table');
    const exportCsvButton = document.getElementById('export-margin-csv');

    // Charts
    let marginDistributionChart = null;
    let topMarginProductsChart = null;

    // Load data on page load
    loadCategories();
    loadMarginData();

    // Event listeners
    applyFiltersButton.addEventListener('click', loadMarginData);
    resetFiltersButton.addEventListener('click', resetFilters);
    exportCsvButton.addEventListener('click', exportMarginCsv);

    // Load categories for filter
    function loadCategories() {
        fetch('/api/inventory/categories')
            .then(response => response.json())
            .then(categories => {
                categoryFilterElement.innerHTML = '<option value="">All Categories</option>';
                categories.forEach(category => {
                    const option = document.createElement('option');
                    option.value = category;
                    option.textContent = category;
                    categoryFilterElement.appendChild(option);
                });
            })
            .catch(error => {
                console.error('Error loading categories:', error);
            });
    }

    // Load margin data with optional filters
    function loadMarginData() {
        // Get filter values
        const category = categoryFilterElement.value;
        const searchTerm = searchFilterElement.value;

        // Build query string
        let queryParams = [];

        if (category) {
            queryParams.push(`category=${encodeURIComponent(category)}`);
        }
        if (searchTerm) {
            queryParams.push(`search=${encodeURIComponent(searchTerm)}`);
        }

        const queryString = queryParams.length > 0 ? `?${queryParams.join('&')}` : '';

        fetch(`/api/reports/profit-margin${queryString}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    displayMarginData(data.item_margins);
                    createMarginDistributionChart(data.item_margins);
                    createTopMarginProductsChart(data.item_margins);
                } else {
                    throw new Error(data.error || 'Invalid data format');
                }
            })
            .catch(error => {
                console.error('Error loading margin data:', error);
                marginTableElement.innerHTML = '<tr><td colspan="9" class="text-center text-danger">Error loading margin data</td></tr>';
            });
    }

    // Display margin data in table
    function displayMarginData(items) {
        if (items.length === 0) {
            marginTableElement.innerHTML = '<tr><td colspan="9" class="text-center">No items found</td></tr>';
            return;
        }

        let html = '';

        items.forEach(item => {
            // Determine row color based on margin percentage
            let rowClass = '';
            if (item.margin_percentage >= 50) {
                rowClass = 'table-success';
            } else if (item.margin_percentage >= 30) {
                rowClass = 'table-info';
            } else if (item.margin_percentage >= 15) {
                rowClass = 'table-warning';
            } else if (item.margin_percentage <= 0) {
                rowClass = 'table-danger';
            }

            // Calculate markup percentage
            const markup = item.buying_price > 0 ? ((item.margin_amount / item.buying_price) * 100) : 0;

            html += `
            <tr class="${rowClass}">
                <td>
                    <div class="fw-bold">${item.item_name}</div>
                    ${item.category ? `<small class="text-muted">${item.category}</small>` : ''}
                </td>
                <td>${item.item_id || '-'}</td>
                <td>${item.category || 'Uncategorized'}</td>
                <td>${item.units_sold || 0}</td>
                <td><span class="currency-symbol">TZS</span> ${item.buying_price.toLocaleString()}</td>
                <td><span class="currency-symbol">TZS</span> ${item.selling_price.toLocaleString()}</td>
                <td class="text-info"><span class="currency-symbol">TZS</span> ${item.margin_amount.toLocaleString()}</td>
                <td class="fw-bold">${item.margin_percentage.toFixed(2)}%</td>
                <td>${markup.toFixed(2)}%</td>
            </tr>
            `;
        });

        marginTableElement.innerHTML = html;
    }

    // Create margin distribution chart
    function createMarginDistributionChart(items) {
        const ctx = document.getElementById('margin-distribution-chart').getContext('2d');
        const colors = getThemeColors();

        // Define margin ranges
        const ranges = [
            { label: 'Negative', min: -100, max: 0, color: colors.danger },
            { label: 'Low (0-15%)', min: 0, max: 15, color: colors.warning },
            { label: 'Medium (15-30%)', min: 15, max: 30, color: colors.info },
            { label: 'Good (30-50%)', min: 30, max: 50, color: colors.success },
            { label: 'Excellent (50%+)', min: 50, max: 1000, color: colors.teal }
        ];

        // Count items in each range
        const data = ranges.map(range => {
            return {
                label: range.label,
                count: items.filter(item => 
                    item.margin_percentage >= range.min && item.margin_percentage < range.max
                ).length,
                color: range.color
            };
        });

        // Destroy existing chart if it exists
        if (marginDistributionChart) {
            marginDistributionChart.destroy();
        }

        // Create new chart
        marginDistributionChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ranges.map(r => r.label),
                datasets: [{
                    data: data.map(d => d.count),
                    backgroundColor: data.map(d => d.color),
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: colors.chartText
                        }
                    },
                    tooltip: {
                        backgroundColor: colors.tooltipBackground,
                        titleColor: colors.tooltipText,
                        bodyColor: colors.tooltipText,
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return `${label}: ${value} items (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Create top margin products chart
    function createTopMarginProductsChart(items) {
        const ctx = document.getElementById('top-margin-products-chart').getContext('2d');
        const colors = getThemeColors();

        // Sort by margin percentage and take top 10
        const topItems = items
            .sort((a, b) => b.margin_percentage - a.margin_percentage)
            .slice(0, 10);

        // Destroy existing chart if it exists
        if (topMarginProductsChart) {
            topMarginProductsChart.destroy();
        }

        // Create new chart
        topMarginProductsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: topItems.map(item => item.item_name),
                datasets: [{
                    label: 'Margin %',
                    data: topItems.map(item => item.margin_percentage),
                    backgroundColor: colors.success,
                    borderColor: colors.success.replace('0.8', '1'),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            },
                            color: colors.chartSecondaryText
                        },
                        grid: {
                            color: colors.chartGrid
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: colors.tooltipBackground,
                        titleColor: colors.tooltipText,
                        bodyColor: colors.tooltipText,
                        callbacks: {
                            label: function(context) {
                                return `Margin: ${context.raw.toFixed(2)}%`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Reset filters
    function resetFilters() {
        categoryFilterElement.value = '';
        searchFilterElement.value = '';
        loadMarginData();
    }

    // Export margin data as CSV
    function exportMarginCsv() {
        const category = categoryFilterElement.value;
        const searchTerm = searchFilterElement.value;

        let queryParams = ['format=csv'];

        if (category) {
            queryParams.push(`category=${encodeURIComponent(category)}`);
        }
        if (searchTerm) {
            queryParams.push(`search=${encodeURIComponent(searchTerm)}`);
        }

        const queryString = `?${queryParams.join('&')}`;
        window.open(`/api/reports/profit-margin${queryString}`, '_blank');
    }
});