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
    
    // Load inventory categories for filter dropdown
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
        
        fetch(`/api/inventory${queryString}`)
            .then(response => response.json())
            .then(data => {
                if (data && Array.isArray(data)) {
                    displayMarginData(data);
                    createMarginDistributionChart(data);
                    createTopMarginProductsChart(data);
                } else {
                    throw new Error('Invalid data format');
                }
            })
            .catch(error => {
                console.error('Error loading margin data:', error);
                marginTableElement.innerHTML = '<tr><td colspan="10" class="text-center text-danger">Error loading margin data</td></tr>';
            });
    }
    
    // Display margin data in table
    function displayMarginData(items) {
        if (items.length === 0) {
            marginTableElement.innerHTML = '<tr><td colspan="10" class="text-center">No items found</td></tr>';
            return;
        }
        
        // Sort items by retail margin percentage (descending)
        items.sort((a, b) => {
            const aMarginPct = calculateMarginPercentage(a.buying_price, a.selling_price_retail);
            const bMarginPct = calculateMarginPercentage(b.buying_price, b.selling_price_retail);
            return bMarginPct - aMarginPct;
        });
        
        let html = '';
        
        items.forEach(item => {
            // Calculate margins
            const retailMargin = item.selling_price_retail - item.buying_price;
            const wholesaleMargin = item.selling_price_wholesale - item.buying_price;
            
            // Calculate margin percentages
            const retailMarginPct = calculateMarginPercentage(item.buying_price, item.selling_price_retail);
            const wholesaleMarginPct = calculateMarginPercentage(item.buying_price, item.selling_price_wholesale);
            
            // Determine row color based on retail margin percentage
            let rowClass = '';
            if (retailMarginPct >= 50) {
                rowClass = 'table-success';
            } else if (retailMarginPct >= 30) {
                rowClass = 'table-info';
            } else if (retailMarginPct >= 15) {
                rowClass = 'table-warning';
            } else if (retailMarginPct <= 0) {
                rowClass = 'table-danger';
            }
            
            html += `
            <tr class="${rowClass}">
                <td>${item.name}</td>
                <td>${item.sku || '-'}</td>
                <td>${item.category || 'Uncategorized'}</td>
                <td><span class="currency-symbol">TZS</span> ${item.buying_price.toLocaleString()}</td>
                <td><span class="currency-symbol">TZS</span> ${item.selling_price_retail.toLocaleString()}</td>
                <td><span class="currency-symbol">TZS</span> ${item.selling_price_wholesale.toLocaleString()}</td>
                <td><span class="currency-symbol">TZS</span> ${retailMargin.toLocaleString()}</td>
                <td><span class="currency-symbol">TZS</span> ${wholesaleMargin.toLocaleString()}</td>
                <td>${retailMarginPct.toFixed(2)}%</td>
                <td>${wholesaleMarginPct.toFixed(2)}%</td>
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
            { label: 'Excellent (>50%)', min: 50, max: 1000, color: colors.teal }
        ];
        
        // Count items in each range
        const rangeCounts = ranges.map(range => {
            return {
                label: range.label,
                count: items.filter(item => {
                    const marginPct = calculateMarginPercentage(item.buying_price, item.selling_price_retail);
                    return marginPct > range.min && marginPct <= range.max;
                }).length,
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
                labels: rangeCounts.map(range => range.label),
                datasets: [{
                    data: rangeCounts.map(range => range.count),
                    backgroundColor: rangeCounts.map(range => range.color),
                    borderColor: colors.chartBorder,
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
        
        // Sort items by retail margin and take top 10
        const topItems = [...items].sort((a, b) => {
            const aMargin = a.selling_price_retail - a.buying_price;
            const bMargin = b.selling_price_retail - b.buying_price;
            return bMargin - aMargin;
        }).slice(0, 10);
        
        // Prepare data for chart
        const labels = topItems.map(item => item.name.length > 15 ? item.name.substring(0, 15) + '...' : item.name);
        const margins = topItems.map(item => item.selling_price_retail - item.buying_price);
        const marginPercentages = topItems.map(item => calculateMarginPercentage(item.buying_price, item.selling_price_retail));
        
        // Destroy existing chart if it exists
        if (topMarginProductsChart) {
            topMarginProductsChart.destroy();
        }
        
        // Create new chart
        topMarginProductsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Margin Amount',
                        data: margins,
                        backgroundColor: colors.success,
                        borderColor: colors.success.replace('0.8', '1'),
                        borderWidth: 1,
                        order: 2
                    },
                    {
                        label: 'Margin %',
                        data: marginPercentages,
                        backgroundColor: colors.info,
                        borderColor: colors.info.replace('0.8', '1'),
                        borderWidth: 1,
                        type: 'line',
                        order: 1,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Margin Amount (TZS)',
                            color: colors.chartText
                        },
                        ticks: {
                            callback: function(value) {
                                return 'TZS ' + value.toLocaleString();
                            },
                            color: colors.chartSecondaryText
                        },
                        grid: {
                            color: colors.chartGrid
                        }
                    },
                    y1: {
                        beginAtZero: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Margin %',
                            color: colors.chartText
                        },
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            },
                            color: colors.chartSecondaryText
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    },
                    x: {
                        ticks: {
                            color: colors.chartSecondaryText
                        },
                        grid: {
                            color: colors.chartGrid
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        backgroundColor: colors.tooltipBackground,
                        titleColor: colors.tooltipText,
                        bodyColor: colors.tooltipText,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.datasetIndex === 0) {
                                    label += 'TZS ' + context.raw.toLocaleString();
                                } else {
                                    label += context.raw.toFixed(2) + '%';
                                }
                                return label;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Reset all filters
    function resetFilters() {
        categoryFilterElement.value = '';
        searchFilterElement.value = '';
        loadMarginData();
    }
    
    // Export margin data to CSV
    function exportMarginCsv() {
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
        
        fetch(`/api/inventory${queryString}`)
            .then(response => response.json())
            .then(data => {
                if (data && Array.isArray(data)) {
                    // Prepare CSV data
                    const csvRows = [];
                    
                    // Add header row
                    csvRows.push([
                        'Name',
                        'SKU',
                        'Category',
                        'Buying Price (TZS)',
                        'Selling Price Retail (TZS)',
                        'Selling Price Wholesale (TZS)',
                        'Retail Margin (TZS)',
                        'Wholesale Margin (TZS)',
                        'Retail Margin %',
                        'Wholesale Margin %'
                    ].join(','));
                    
                    // Add data rows
                    data.forEach(item => {
                        // Calculate margins
                        const retailMargin = item.selling_price_retail - item.buying_price;
                        const wholesaleMargin = item.selling_price_wholesale - item.buying_price;
                        
                        // Calculate margin percentages
                        const retailMarginPct = calculateMarginPercentage(item.buying_price, item.selling_price_retail);
                        const wholesaleMarginPct = calculateMarginPercentage(item.buying_price, item.selling_price_wholesale);
                        
                        // Format CSV row
                        csvRows.push([
                            `"${item.name.replace(/"/g, '""')}"`,
                            `"${(item.sku || '').replace(/"/g, '""')}"`,
                            `"${(item.category || 'Uncategorized').replace(/"/g, '""')}"`,
                            item.buying_price,
                            item.selling_price_retail,
                            item.selling_price_wholesale,
                            retailMargin,
                            wholesaleMargin,
                            retailMarginPct.toFixed(2),
                            wholesaleMarginPct.toFixed(2)
                        ].join(','));
                    });
                    
                    // Create and download CSV file
                    const csvString = csvRows.join('\n');
                    const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.setAttribute('href', url);
                    link.setAttribute('download', `margin-report-${new Date().toISOString().slice(0, 10)}.csv`);
                    link.style.visibility = 'hidden';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                } else {
                    throw new Error('Invalid data format');
                }
            })
            .catch(error => {
                console.error('Error exporting margin data:', error);
                alert('Error exporting margin data. Please try again.');
            });
    }
    
    // Calculate margin percentage safely
    function calculateMarginPercentage(buyingPrice, sellingPrice) {
        if (!buyingPrice || buyingPrice <= 0) {
            return sellingPrice > 0 ? 100 : 0;
        }
        return ((sellingPrice - buyingPrice) / buyingPrice) * 100;
    }
});