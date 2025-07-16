/**
 * Centralized API handler with authentication and error handling
 */
class APIHandler {
    constructor() {
        this.baseURL = window.location.origin;
        this.isAuthenticated = false;
        this.checkAuthenticationStatus();
    }

    /**
     * Check if user is authenticated by testing a protected endpoint
     */
    async checkAuthenticationStatus() {
        try {
            const response = await fetch('/api/shop/details');
            this.isAuthenticated = response.ok && response.status !== 302;
        } catch (error) {
            this.isAuthenticated = false;
        }
    }

    /**
     * Enhanced fetch with authentication handling
     */
    async fetchWithAuth(url, options = {}) {
        const config = {
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            // Handle authentication redirects
            if (response.status === 302 || response.status === 401) {
                this.isAuthenticated = false;
                console.warn(`Authentication required for ${url}`);
                // Redirect to login if not authenticated
                if (window.location.pathname !== '/login' && window.location.pathname !== '/') {
                    window.location.href = '/login';
                }
                return {
                    ok: false,
                    status: 401,
                    json: async () => ({ error: 'Authentication required' })
                };
            }

            return response;
            
        } catch (error) {
            console.error(`API Error for ${url}:`, error);
            return {
                ok: false,
                status: 500,
                json: async () => ({ error: error.message })
            };
        }
    }

    /**
     * Get dashboard summary data
     */
    async getDashboardSummary() {
        try {
            const response = await this.fetchWithAuth('/api/reports/stock-status');
            return response.ok ? await response.json() : null;
        } catch (error) {
            console.error('Error loading dashboard summary:', error);
            return null;
        }
    }

    /**
     * Get top selling items - calculated from sales data
     */
    async getTopSellingItems() {
        try {
            const response = await this.fetchWithAuth('/api/sales');
            if (!response.ok) return [];
            
            const salesData = await response.json();
            const itemSales = {};
            
            if (salesData && Array.isArray(salesData)) {
                salesData.forEach(sale => {
                    if (sale.sale_items) {
                        sale.sale_items.forEach(item => {
                            const itemName = item.item_name || item.name;
                            itemSales[itemName] = (itemSales[itemName] || 0) + item.quantity;
                        });
                    }
                });
            }
            
            return Object.entries(itemSales)
                .map(([name, quantity]) => ({ name, quantity }))
                .sort((a, b) => b.quantity - a.quantity)
                .slice(0, 10);
        } catch (error) {
            console.error('Error loading top selling items:', error);
            return [];
        }
    }

    /**
     * Get category breakdown
     */
    async getCategoryBreakdown() {
        try {
            const response = await this.fetchWithAuth('/api/reports/category-breakdown');
            return response.ok ? await response.json() : {};
        } catch (error) {
            console.error('Error loading category breakdown:', error);
            return {};
        }
    }



    /**
     * Get on-demand products
     */
    async getOnDemandProducts() {
        try {
            const response = await this.fetchWithAuth('/api/on-demand?active_only=true');
            return response.ok ? await response.json() : [];
        } catch (error) {
            console.error('Error loading on-demand products:', error);
            return [];
        }
    }

    /**
     * Get financial summary
     */
    async getFinancialSummary() {
        try {
            const response = await this.fetchWithAuth('/api/finance/summaries/monthly');
            return response.ok ? await response.json() : null;
        } catch (error) {
            console.error('Error loading financial summary:', error);
            return null;
        }
    }
}

// Global API handler instance
window.apiHandler = new APIHandler();