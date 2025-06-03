
// Inventory System - Profit Calculation Utility
// Handles both realistic (with expenses) and simplified (without expenses) profit calculations

class ProfitCalculator {
    constructor() {
        this.includeExpenses = false; // Default to simplified view
        this.globalExpenseRate = 0.10; // 10% default expense rate for realistic calculations
    }

    /**
     * Calculate Gross Profit per item
     * Gross Profit = Selling Price - Buying Price
     */
    calculateGrossProfit(sellingPrice, buyingPrice) {
        const grossProfit = (sellingPrice || 0) - (buyingPrice || 0);
        return Math.max(0, grossProfit); // Ensure non-negative
    }

    /**
     * Calculate Net Profit (Realistic View)
     * Net Profit = Gross Profit - Expenses
     */
    calculateNetProfitRealistic(grossProfit, expenses = null) {
        if (expenses === null) {
            // Use global expense rate if no specific expenses provided
            expenses = grossProfit * this.globalExpenseRate;
        }
        return grossProfit - expenses;
    }

    /**
     * Calculate Net Profit (Simplified View)
     * Net Profit = Gross Profit (ignoring expenses)
     */
    calculateNetProfitSimplified(grossProfit) {
        return grossProfit;
    }

    /**
     * Calculate profit margin percentage
     */
    calculateProfitMargin(profit, sellingPrice) {
        if (!sellingPrice || sellingPrice <= 0) return 0;
        return (profit / sellingPrice) * 100;
    }

    /**
     * Calculate markup percentage
     */
    calculateMarkup(profit, buyingPrice) {
        if (!buyingPrice || buyingPrice <= 0) return 0;
        return (profit / buyingPrice) * 100;
    }

    /**
     * Get comprehensive profit analysis for an item
     */
    analyzeItemProfit(item, options = {}) {
        const sellingPrice = item.selling_price_retail || item.price || 0;
        const buyingPrice = item.buying_price || 0;
        const quantity = item.quantity || 0;
        const expenses = options.expenses || null;

        // Basic calculations
        const grossProfit = this.calculateGrossProfit(sellingPrice, buyingPrice);
        const netProfitRealistic = this.calculateNetProfitRealistic(grossProfit, expenses);
        const netProfitSimplified = this.calculateNetProfitSimplified(grossProfit);

        // Percentages
        const grossMargin = this.calculateProfitMargin(grossProfit, sellingPrice);
        const netMarginRealistic = this.calculateProfitMargin(netProfitRealistic, sellingPrice);
        const netMarginSimplified = this.calculateProfitMargin(netProfitSimplified, sellingPrice);
        const markup = this.calculateMarkup(grossProfit, buyingPrice);

        // Total calculations (considering quantity)
        const totalGrossProfit = grossProfit * quantity;
        const totalNetProfitRealistic = netProfitRealistic * quantity;
        const totalNetProfitSimplified = netProfitSimplified * quantity;

        return {
            item: {
                name: item.name,
                sku: item.sku,
                category: item.category,
                quantity: quantity
            },
            prices: {
                buying_price: buyingPrice,
                selling_price: sellingPrice
            },
            profit_per_unit: {
                gross_profit: grossProfit,
                net_profit_realistic: netProfitRealistic,
                net_profit_simplified: netProfitSimplified
            },
            margins: {
                gross_margin: grossMargin,
                net_margin_realistic: netMarginRealistic,
                net_margin_simplified: netMarginSimplified,
                markup: markup
            },
            total_profit: {
                total_gross_profit: totalGrossProfit,
                total_net_profit_realistic: totalNetProfitRealistic,
                total_net_profit_simplified: totalNetProfitSimplified
            },
            view_mode: this.includeExpenses ? 'realistic' : 'simplified'
        };
    }

    /**
     * Analyze profits for multiple items
     */
    analyzeInventoryProfit(items, options = {}) {
        const analysis = items.map(item => this.analyzeItemProfit(item, options));
        
        // Calculate totals
        const totals = {
            total_gross_profit: 0,
            total_net_profit_realistic: 0,
            total_net_profit_simplified: 0,
            total_revenue: 0,
            total_cost: 0
        };

        analysis.forEach(item => {
            totals.total_gross_profit += item.total_profit.total_gross_profit;
            totals.total_net_profit_realistic += item.total_profit.total_net_profit_realistic;
            totals.total_net_profit_simplified += item.total_profit.total_net_profit_simplified;
            totals.total_revenue += (item.prices.selling_price * item.item.quantity);
            totals.total_cost += (item.prices.buying_price * item.item.quantity);
        });

        // Calculate overall margins
        const overallGrossMargin = totals.total_revenue > 0 ? 
            (totals.total_gross_profit / totals.total_revenue) * 100 : 0;
        const overallNetMarginRealistic = totals.total_revenue > 0 ? 
            (totals.total_net_profit_realistic / totals.total_revenue) * 100 : 0;
        const overallNetMarginSimplified = totals.total_revenue > 0 ? 
            (totals.total_net_profit_simplified / totals.total_revenue) * 100 : 0;

        return {
            items: analysis,
            summary: {
                ...totals,
                overall_gross_margin: overallGrossMargin,
                overall_net_margin_realistic: overallNetMarginRealistic,
                overall_net_margin_simplified: overallNetMarginSimplified,
                item_count: items.length,
                view_mode: this.includeExpenses ? 'realistic' : 'simplified'
            }
        };
    }

    /**
     * Set calculation mode
     */
    setCalculationMode(includeExpenses, expenseRate = null) {
        this.includeExpenses = includeExpenses;
        if (expenseRate !== null) {
            this.globalExpenseRate = expenseRate / 100; // Convert percentage to decimal
        }
    }

    /**
     * Format currency for display
     */
    formatCurrency(amount, currency = 'TZS') {
        return `${currency} ${amount.toLocaleString()}`;
    }

    /**
     * Format percentage for display
     */
    formatPercentage(percentage) {
        return `${percentage.toFixed(2)}%`;
    }
}

// Export for use in other modules
window.ProfitCalculator = ProfitCalculator;
