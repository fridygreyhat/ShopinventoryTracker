
document.addEventListener('DOMContentLoaded', function() {
    let products = [];

    // Function to fetch products (equivalent to your useEffect)
    function fetchProducts() {
        fetch('/api/inventory')  // Using your existing inventory API
            .then(response => response.json())
            .then(data => {
                products = data;
                console.log('Products loaded:', products);
                // You can call other functions here to update the UI
                displayProducts(products);
            })
            .catch(error => {
                console.error('Error fetching products:', error);
            });
    }

    // Function to display products
    function displayProducts(productList) {
        // Add your UI update logic here
        console.log('Displaying products:', productList);
    }

    // Call the function when the page loads (equivalent to useEffect with empty dependency array)
    fetchProducts();

    // If you need to refresh products, you can call fetchProducts() again
    window.refreshProducts = fetchProducts;
});
