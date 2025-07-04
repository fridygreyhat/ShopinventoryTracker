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
                // Return a mock response that indicates auth failure
                return {
                    ok: false,
                    status: 401,
                    json: async () => ({ error: 'Authentication required' })
                };
            }

            return response;
            
        } catch (error) {
            console.error(`API Error for ${url}:`, error);
            // Return a mock response that indicates network error
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
     * Get top selling items
     */
    async getTopSellingItems() {
        try {
            const response = await this.fetchWithAuth('/api/sales/performance/top');
            return response.ok ? await response.json() : [];
        } catch (error) {
            console.error('Error loading top selling items:', error);
            return [];
        }
    }

    /**
     * Get slow moving items
     */
    async getSlowMovingItems() {
        try {
            const response = await this.fetchWithAuth('/api/sales/performance/slow');
            return response.ok ? await response.json() : [];
        } catch (error) {
            console.error('Error loading slow moving items:', error);
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
     * Get slow moving items
     */
    async getSlowMovingItems() {
        try {
            const response = await this.fetchWithAuth('/api/sales/performance/slow');
            return response.ok ? await response.json() : [];
        } catch (error) {
            console.error('Error loading slow moving items:', error);
            return [];
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