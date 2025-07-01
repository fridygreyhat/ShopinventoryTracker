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
                return { success: false, data: null, authenticated: false };
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            return { success: true, data, authenticated: true };
            
        } catch (error) {
            console.error(`API Error for ${url}:`, error);
            return { success: false, error: error.message, authenticated: this.isAuthenticated };
        }
    }

    /**
     * Get dashboard summary data
     */
    async getDashboardSummary() {
        const result = await this.fetchWithAuth('/api/reports/stock-status');
        return result.success ? result.data : null;
    }

    /**
     * Get top selling items
     */
    async getTopSellingItems() {
        const result = await this.fetchWithAuth('/api/sales/performance/top');
        return result.success ? result.data : [];
    }

    /**
     * Get slow moving items
     */
    async getSlowMovingItems() {
        const result = await this.fetchWithAuth('/api/sales/performance/slow');
        return result.success ? result.data : [];
    }

    /**
     * Get category breakdown
     */
    async getCategoryBreakdown() {
        const result = await this.fetchWithAuth('/api/reports/category-breakdown');
        return result.success ? result.data : {};
    }

    /**
     * Get on-demand products
     */
    async getOnDemandProducts() {
        const result = await this.fetchWithAuth('/api/on-demand?active_only=true');
        return result.success ? result.data : [];
    }

    /**
     * Get financial summary
     */
    async getFinancialSummary() {
        const result = await this.fetchWithAuth('/api/finance/summaries/monthly');
        return result.success ? result.data : null;
    }
}

// Global API handler instance
window.apiHandler = new APIHandler();