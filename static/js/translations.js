
// Translations object
const translations = {
    en: {
        dashboard: "Dashboard",
        inventory: "Inventory",
        margin: "Margin",
        onDemand: "On-Demand Products",
        sales: "Sales",
        reports: "Reports",
        finance: "Finance",
        settings: "Settings",
        totalItems: "Total Items",
        totalStock: "Total Stock",
        lowStockItems: "Low Stock Items",
        inventoryValue: "Inventory Value",
        financialSummary: "Financial Summary",
        viewReports: "View Reports",
        income: "Income",
        expenses: "Expenses",
        netProfit: "Net Profit",
        thisMonth: "This Month",
        inventoryHealth: "Inventory Health Overview",
        stockLevels: "Stock Levels by Category",
        inventoryValueByCategory: "Inventory Value by Category",
        lowStockItemsTitle: "Low Stock Items",
        viewAllInventory: "View All Inventory",
        topSelling: "Top Selling Items",
        slowMoving: "Slow Moving Items",
        onDemandProducts: "On-Demand Products",
        manageOnDemand: "Manage On-Demand Products",
        name: "Name",
        sku: "SKU",
        category: "Category",
        quantity: "Quantity",
        price: "Price",
        action: "Action",
        update: "Update"
    },
    sw: {
        dashboard: "Dashibodi",
        inventory: "Hesabu ya Mali",
        margin: "Faida",
        onDemand: "Bidhaa za Agizo",
        sales: "Mauzo",
        reports: "Ripoti",
        finance: "Fedha",
        settings: "Mipangilio",
        totalItems: "Jumla ya Bidhaa",
        totalStock: "Jumla ya Stoki",
        lowStockItems: "Bidhaa za Stoki Ndogo",
        inventoryValue: "Thamani ya Mali",
        financialSummary: "Muhtasari wa Kifedha",
        viewReports: "Tazama Ripoti",
        income: "Mapato",
        expenses: "Matumizi",
        netProfit: "Faida Halisi",
        thisMonth: "Mwezi Huu",
        inventoryHealth: "Muhtasari wa Afya ya Mali",
        stockLevels: "Viwango vya Stoki kwa Kategoria",
        inventoryValueByCategory: "Thamani ya Mali kwa Kategoria",
        lowStockItemsTitle: "Bidhaa za Stoki Ndogo",
        viewAllInventory: "Tazama Mali Zote",
        topSelling: "Bidhaa Zinazouza Zaidi",
        slowMoving: "Bidhaa Zinazouza Polepole",
        onDemandProducts: "Bidhaa za Agizo",
        manageOnDemand: "Simamia Bidhaa za Agizo",
        name: "Jina",
        sku: "SKU",
        category: "Kategoria",
        quantity: "Kiasi",
        price: "Bei",
        action: "Hatua",
        update: "Sasisha"
    }
};

// Function to update page content
function updatePageLanguage(lang) {
    // Save language preference
    localStorage.setItem('preferred_language', lang);
    
    // Update all translatable elements
    document.querySelectorAll('[data-translate]').forEach(element => {
        const key = element.getAttribute('data-translate');
        if (translations[lang][key]) {
            element.textContent = translations[lang][key];
        }
    });
}

// Initialize language selector
document.addEventListener('DOMContentLoaded', function() {
    // Handle sidebar language selector (if exists)
    const languageSelector = document.getElementById('languageSelector');
    if (languageSelector) {
        // Set initial language
        const savedLanguage = localStorage.getItem('preferred_language') || 'en';
        languageSelector.value = savedLanguage;
        updatePageLanguage(savedLanguage);

        // Add change event listener
        languageSelector.addEventListener('change', function() {
            updatePageLanguage(this.value);
        });
    }

    // Handle top bar language selector
    const topLanguageOptions = document.querySelectorAll('.language-option');
    const currentLanguageSpan = document.getElementById('currentLanguage');
    
    if (topLanguageOptions.length > 0) {
        // Set initial language display
        const savedLanguage = localStorage.getItem('preferred_language') || 'en';
        updateTopLanguageDisplay(savedLanguage);
        updatePageLanguage(savedLanguage);

        // Add click event listeners to language options
        topLanguageOptions.forEach(option => {
            option.addEventListener('click', function(e) {
                e.preventDefault();
                const selectedLang = this.getAttribute('data-lang');
                updatePageLanguage(selectedLang);
                updateTopLanguageDisplay(selectedLang);
            });
        });
    }
});

// Function to update top language display
function updateTopLanguageDisplay(lang) {
    const currentLanguageSpan = document.getElementById('currentLanguage');
    if (currentLanguageSpan) {
        if (lang === 'en') {
            currentLanguageSpan.textContent = 'English';
        } else if (lang === 'sw') {
            currentLanguageSpan.textContent = 'Kiswahili';
        }
    }
}
