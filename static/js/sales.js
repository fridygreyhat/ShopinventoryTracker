document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const startScanBtn = document.getElementById('startScanBtn');
    const scannerContainer = document.getElementById('scannerContainer');
    const cancelScanBtn = document.getElementById('cancelScanBtn');
    const scanFeedback = document.getElementById('scanFeedback');
    const videoElement = document.getElementById('video');
    
    // Search and cart elements
    const productSearchInput = document.getElementById('productSearchInput');
    const searchProductsBtn = document.getElementById('searchProductsBtn');
    const productResultsTable = document.getElementById('productResultsTable');
    const cartTableBody = document.getElementById('cartTableBody');
    const cartCount = document.getElementById('cartCount');
    const cartSubtotal = document.getElementById('cartSubtotal');
    const cartDiscount = document.getElementById('cartDiscount');
    const cartDiscountType = document.getElementById('cartDiscountType');
    const cartTotal = document.getElementById('cartTotal');
    const clearCartBtn = document.getElementById('clearCartBtn');
    const saleTypeSelector = document.getElementById('saleTypeSelector');
    
    // Checkout elements
    const paymentMethod = document.getElementById('paymentMethod');
    const mobileMoneyFields = document.getElementById('mobileMoneyFields');
    const paymentAmount = document.getElementById('paymentAmount');
    const completeTransactionBtn = document.getElementById('completeTransactionBtn');
    const createInvoiceBtn = document.getElementById('createInvoiceBtn');
    
    // Discount modal elements
    const discountType = document.getElementById('discountType');
    const discountValue = document.getElementById('discountValue');
    const applyDiscountModalBtn = document.getElementById('applyDiscountModalBtn');
    
    // Variables
    let codeReader = null;
    let selectedDeviceId = null;
    let cart = [];
    let currentDiscount = {
        type: 'none',
        value: 0
    };
    let searchResults = [];
    let saleType = 'retail'; // Default to retail pricing
    let unitType = 'quantity'; // Default to quantity-based sales
    
    // Initialize
    updateCartDisplay();
    
    // Event Listeners
    
    // Barcode scanner
    startScanBtn.addEventListener('click', startScanner);
    cancelScanBtn.addEventListener('click', stopScanner);
    
    // Product search
    searchProductsBtn.addEventListener('click', searchProducts);
    productSearchInput.addEventListener('keyup', function(e) {
        if (e.key === 'Enter') {
            searchProducts();
        }
    });
    
    // Sale type selection
    saleTypeSelector.addEventListener('change', function() {
        saleType = this.value;
        
        // If there are items in the cart, update their prices based on the new sale type
        if (cart.length > 0) {
            cart.forEach(item => {
                if (saleType === 'retail') {
                    item.price = item.selling_price_retail;
                } else {
                    item.price = item.selling_price_wholesale;
                }
                item.total = item.price * item.quantity;
            });
            updateCartDisplay();
        }
        
        // If there are search results displayed, update their displayed prices
        if (searchResults.length > 0) {
            displaySearchResults(searchResults);
        }
    });
    
    // Unit type selection
    const unitTypeSelector = document.getElementById('unitTypeSelector');
    unitTypeSelector.addEventListener('change', function() {
        unitType = this.value;
        // Update quantity input step and min values based on unit type
        document.querySelectorAll('.item-qty').forEach(input => {
            if (unitType === 'weight') {
                input.setAttribute('step', '0.1');
                input.setAttribute('min', '0.1');
            } else {
                input.setAttribute('step', '1');
                input.setAttribute('min', '1');
            }
        });
    });
    
    // Cart management
    clearCartBtn.addEventListener('click', clearCart);
    
    // Payment method toggle
    paymentMethod.addEventListener('change', function() {
        if (this.value === 'mobile_money') {
            mobileMoneyFields.classList.remove('d-none');
        } else {
            mobileMoneyFields.classList.add('d-none');
        }
    });
    
    // Set payment amount to match cart total when cart changes
    paymentAmount.addEventListener('focus', function() {
        this.value = parseFloat(cartTotal.textContent.replace(/,/g, ''));
    });
    
    // Checkout
    completeTransactionBtn.addEventListener('click', completeTransaction);
    createInvoiceBtn.addEventListener('click', createInvoice);
    
    // Discount application
    applyDiscountModalBtn.addEventListener('click', applyDiscount);
    
    // Barcode Scanner Functions
    function startScanner() {
        scannerContainer.classList.remove('d-none');
        scanFeedback.textContent = 'Initializing camera...';
        
        if (!codeReader) {
            codeReader = new ZXing.BrowserMultiFormatReader();
        }
        
        codeReader.listVideoInputDevices()
            .then((videoInputDevices) => {
                if (videoInputDevices.length === 0) {
                    scanFeedback.textContent = 'No camera detected';
                    return;
                }
                
                // Use the first camera by default
                selectedDeviceId = videoInputDevices[0].deviceId;
                
                // If there's an environment-facing camera, prefer that
                const environmentCamera = videoInputDevices.find(device => 
                    device.label && device.label.toLowerCase().includes('back'));
                
                if (environmentCamera) {
                    selectedDeviceId = environmentCamera.deviceId;
                }
                
                startDecoding(selectedDeviceId);
            })
            .catch(err => {
                console.error('Error accessing camera:', err);
                scanFeedback.textContent = 'Camera access denied or error';
            });
    }
    
    function startDecoding(deviceId) {
        codeReader.decodeFromVideoDevice(deviceId, videoElement, (result, err) => {
            if (result) {
                // Successfully scanned a barcode
                scanFeedback.textContent = `Scanned: ${result.text}`;
                
                // Stop scanning
                stopScanner();
                
                // Search for the product with this barcode/SKU
                productSearchInput.value = result.text;
                searchProducts();
            }
            
            if (err && !(err instanceof ZXing.NotFoundException)) {
                console.error('Scanning error:', err);
                scanFeedback.textContent = 'Error during scanning';
            }
        });
        
        scanFeedback.textContent = 'Position barcode in the center';
    }
    
    function stopScanner() {
        if (codeReader) {
            codeReader.reset();
            scannerContainer.classList.add('d-none');
        }
    }
    
    // Product Search Functions
    function searchProducts() {
        const query = productSearchInput.value.trim();
        
        if (!query) {
            productResultsTable.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Enter a search term</td></tr>';
            return;
        }
        
        // Show loading state
        productResultsTable.innerHTML = '<tr><td colspan="6" class="text-center"><div class="spinner-border spinner-border-sm text-secondary" role="status"></div> Searching...</td></tr>';
        
        // Make API request to search inventory
        fetch(`/api/inventory?search=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(items => {
                searchResults = items;
                displaySearchResults(items);
            })
            .catch(error => {
                console.error('Error searching products:', error);
                productResultsTable.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Error searching products</td></tr>';
            });
    }
    
    function displaySearchResults(items) {
        if (items.length === 0) {
            productResultsTable.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No products found</td></tr>';
            return;
        }
        
        let html = '';
        
        items.forEach(item => {
            // Determine which price to display based on the sale type
            const displayPrice = saleType === 'retail' 
                ? item.selling_price_retail 
                : item.selling_price_wholesale;
            
            html += `
                <tr>
                    <td>${item.name}</td>
                    <td>${item.sku || 'N/A'}</td>
                    <td>${item.category || 'Uncategorized'}</td>
                    <td><span class="currency-symbol">TZS</span> ${displayPrice.toLocaleString()}</td>
                    <td>${item.quantity}</td>
                    <td>
                        <button class="btn btn-sm btn-primary add-to-cart" data-id="${item.id}">
                            <i class="fas fa-plus"></i>
                        </button>
                    </td>
                </tr>
            `;
        });
        
        productResultsTable.innerHTML = html;
        
        // Add event listeners to Add buttons
        document.querySelectorAll('.add-to-cart').forEach(button => {
            button.addEventListener('click', function() {
                const itemId = this.getAttribute('data-id');
                addToCart(itemId);
            });
        });
    }
    
    // Cart Functions
    function addToCart(itemId) {
        const item = searchResults.find(item => item.id == itemId);
        
        if (!item) {
            console.error('Item not found:', itemId);
            return;
        }
        
        // Check if the item is already in the cart
        const existingItemIndex = cart.findIndex(cartItem => cartItem.id == itemId);
        
        if (existingItemIndex >= 0) {
            // Increment quantity if already in cart
            cart[existingItemIndex].quantity += 1;
            cart[existingItemIndex].total = cart[existingItemIndex].price * cart[existingItemIndex].quantity;
        } else {
            // Add new item to cart
            const price = saleType === 'retail' ? item.selling_price_retail : item.selling_price_wholesale;
            
            cart.push({
                id: item.id,
                name: item.name,
                sku: item.sku,
                price: price,
                selling_price_retail: item.selling_price_retail,
                selling_price_wholesale: item.selling_price_wholesale,
                quantity: 1,
                unit_type: item.unit_type || 'quantity',
                total: price
            });
        }
        
        updateCartDisplay();
    }
    
    function updateCartDisplay() {
        if (cart.length === 0) {
            cartTableBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No items in cart</td></tr>';
            cartCount.textContent = '0 items';
            cartSubtotal.textContent = '0';
            cartTotal.textContent = '0';
            return;
        }
        
        let html = '';
        let subtotal = 0;
        let totalItems = 0;
        
        cart.forEach((item, index) => {
            html += `
                <tr>
                    <td>
                        <div class="fw-bold">${item.name}</div>
                        <div class="small text-muted">${item.sku || 'No SKU'}</div>
                    </td>
                    <td><span class="currency-symbol">TZS</span> ${item.price.toLocaleString()}</td>
                    <td>
                        <div class="input-group input-group-sm">
                            <button class="btn btn-outline-secondary decrease-qty" data-index="${index}">-</button>
                            <input type="number" class="form-control text-center item-qty" 
                                value="${item.quantity}" 
                                data-index="${index}" 
                                min="${item.unit_type === 'weight' ? '0.1' : '1'}" 
                                step="${item.unit_type === 'weight' ? '0.1' : '1'}">
                            <button class="btn btn-outline-secondary increase-qty" data-index="${index}">+</button>
                            <span class="input-group-text">${item.unit_type === 'weight' ? 'kg' : 'pcs'}</span>
                        </div>
                    </td>
                    <td><span class="currency-symbol">TZS</span> ${item.total.toLocaleString()}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-danger remove-item" data-index="${index}">
                            <i class="fas fa-times"></i>
                        </button>
                    </td>
                </tr>
            `;
            
            subtotal += item.total;
            totalItems += item.quantity;
        });
        
        cartTableBody.innerHTML = html;
        cartCount.textContent = `${totalItems} item${totalItems !== 1 ? 's' : ''}`;
        cartSubtotal.textContent = subtotal.toLocaleString();
        
        // Apply discount if any
        let finalTotal = subtotal;
        
        if (currentDiscount.type !== 'none') {
            if (currentDiscount.type === 'percentage') {
                const discountAmount = subtotal * (currentDiscount.value / 100);
                cartDiscountType.textContent = currentDiscount.value + '%';
                cartDiscount.textContent = discountAmount.toLocaleString();
                finalTotal = subtotal - discountAmount;
            } else if (currentDiscount.type === 'fixed') {
                cartDiscountType.textContent = 'TZS';
                cartDiscount.textContent = currentDiscount.value.toLocaleString();
                finalTotal = subtotal - currentDiscount.value;
            }
        } else {
            cartDiscountType.textContent = '-';
            cartDiscount.textContent = '0';
        }
        
        cartTotal.textContent = finalTotal.toLocaleString();
        
        // Add event listeners for quantity adjustment
        document.querySelectorAll('.decrease-qty').forEach(button => {
            button.addEventListener('click', function() {
                const index = this.getAttribute('data-index');
                decreaseQuantity(index);
            });
        });
        
        document.querySelectorAll('.increase-qty').forEach(button => {
            button.addEventListener('click', function() {
                const index = this.getAttribute('data-index');
                increaseQuantity(index);
            });
        });
        
        document.querySelectorAll('.item-qty').forEach(input => {
            input.addEventListener('change', function() {
                const index = this.getAttribute('data-index');
                const newQty = unitType === 'weight' ? parseFloat(this.value) : parseInt(this.value);
                updateQuantity(index, newQty);
            });
        });
        
        document.querySelectorAll('.remove-item').forEach(button => {
            button.addEventListener('click', function() {
                const index = this.getAttribute('data-index');
                removeCartItem(index);
            });
        });
    }
    
    function increaseQuantity(index) {
        cart[index].quantity += 1;
        cart[index].total = cart[index].price * cart[index].quantity;
        updateCartDisplay();
    }
    
    function decreaseQuantity(index) {
        if (cart[index].quantity > 1) {
            cart[index].quantity -= 1;
            cart[index].total = cart[index].price * cart[index].quantity;
            updateCartDisplay();
        }
    }
    
    function updateQuantity(index, newQty) {
        if (newQty > 0) {
            cart[index].quantity = newQty;
            cart[index].total = cart[index].price * cart[index].quantity;
            updateCartDisplay();
        }
    }
    
    function removeCartItem(index) {
        cart.splice(index, 1);
        updateCartDisplay();
    }
    
    function clearCart() {
        cart = [];
        currentDiscount = { type: 'none', value: 0 };
        updateCartDisplay();
    }
    
    // Discount Functions
    function applyDiscount() {
        const type = discountType.value;
        let value = parseFloat(discountValue.value);
        
        if (isNaN(value) || value < 0) {
            value = 0;
        }
        
        if (type === 'percentage' && value > 100) {
            value = 100;
        }
        
        currentDiscount = { type, value };
        updateCartDisplay();
    }
    
    // Transaction Functions
    function completeTransaction() {
        if (cart.length === 0) {
            alert('Please add items to the cart before completing transaction');
            return;
        }
        
        const customerName = document.getElementById('customerName').value || 'Walk-in Customer';
        const customerPhone = document.getElementById('customerPhone').value || '';
        const payment = document.getElementById('paymentMethod').value;
        const amount = parseFloat(document.getElementById('paymentAmount').value) || 0;
        const notes = document.getElementById('saleNotes').value || '';
        
        let mobileInfo = {};
        if (payment === 'mobile_money') {
            mobileInfo = {
                provider: document.getElementById('mobileProvider').value,
                reference: document.getElementById('transactionReference').value
            };
        }
        
        const totalAmount = parseFloat(cartTotal.textContent.replace(/,/g, ''));
        
        if (amount < totalAmount) {
            alert('Payment amount is less than the total');
            return;
        }
        
        // Prepare transaction data
        const transaction = {
            customer: {
                name: customerName,
                phone: customerPhone
            },
            items: cart.map(item => ({
                id: item.id,
                name: item.name,
                sku: item.sku,
                price: item.price,
                quantity: item.quantity,
                total: item.total
            })),
            payment: {
                method: payment,
                amount: amount,
                change: amount - totalAmount,
                mobile_info: payment === 'mobile_money' ? mobileInfo : null
            },
            sale_type: saleType,
            subtotal: parseFloat(cartSubtotal.textContent.replace(/,/g, '')),
            discount: {
                type: currentDiscount.type,
                value: currentDiscount.value,
                amount: parseFloat(cartDiscount.textContent.replace(/,/g, ''))
            },
            total: totalAmount,
            notes: notes,
            date: new Date().toISOString()
        };
        
        // Show loading state
        completeTransactionBtn.disabled = true;
        completeTransactionBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
        
        // Send transaction data to the server
        fetch('/api/sales', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(transaction)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Show success message
            alert('Transaction completed successfully!');
            
            // Reset cart and form
            clearCart();
            document.getElementById('checkoutForm').reset();
            
            // Reset button
            completeTransactionBtn.disabled = false;
            completeTransactionBtn.innerHTML = '<i class="fas fa-check-circle me-1"></i> Complete Transaction';
        })
        .catch(error => {
            console.error('Error completing transaction:', error);
            alert('Failed to complete transaction. Please try again.');
            
            // Reset button
            completeTransactionBtn.disabled = false;
            completeTransactionBtn.innerHTML = '<i class="fas fa-check-circle me-1"></i> Complete Transaction';
        });
    }
    
    function createInvoice() {
        if (cart.length === 0) {
            alert('Please add items to the cart before creating an invoice');
            return;
        }
        
        // Prepare invoice data
        const customerName = document.getElementById('customerName').value || 'Walk-in Customer';
        const customerPhone = document.getElementById('customerPhone').value || '';
        const totalAmount = parseFloat(cartTotal.textContent.replace(/,/g, ''));
        
        // Create a printable invoice in a new window
        const invoiceWindow = window.open('', '_blank');
        invoiceWindow.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Invoice</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 20px;
                    }
                    .invoice-header {
                        text-align: center;
                        margin-bottom: 30px;
                        border-bottom: 1px solid #ddd;
                        padding-bottom: 20px;
                    }
                    .invoice-body {
                        margin-bottom: 30px;
                    }
                    table {
                        width: 100%;
                        border-collapse: collapse;
                        margin-bottom: 20px;
                    }
                    th, td {
                        padding: 10px;
                        border-bottom: 1px solid #ddd;
                        text-align: left;
                    }
                    th {
                        background-color: #f8f8f8;
                    }
                    .text-right {
                        text-align: right;
                    }
                    .total-row {
                        font-weight: bold;
                    }
                    .customer-info {
                        margin-bottom: 20px;
                    }
                    .invoice-footer {
                        margin-top: 30px;
                        border-top: 1px solid #ddd;
                        padding-top: 20px;
                        font-size: 0.9em;
                    }
                    @media print {
                        body {
                            padding: 0;
                        }
                        .no-print {
                            display: none;
                        }
                    }
                </style>
            </head>
            <body>
                <div class="invoice-header">
                    <h1>INVOICE</h1>
                    <p>Shop Inventory Management System</p>
                    <p>Date: ${new Date().toLocaleDateString()}</p>
                    <p>Invoice #: INV-${Date.now().toString().substring(6)}</p>
                </div>
                
                <div class="invoice-body">
                    <div class="customer-info">
                        <h3>Customer Information</h3>
                        <p><strong>Name:</strong> ${customerName}</p>
                        <p><strong>Phone:</strong> ${customerPhone || 'N/A'}</p>
                    </div>
                    
                    <h3>Items</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Item</th>
                                <th>Price</th>
                                <th>Quantity</th>
                                <th class="text-right">Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${cart.map(item => `
                                <tr>
                                    <td>
                                        ${item.name}
                                        <div style="font-size: 0.8em; color: #777;">${item.sku || 'No SKU'}</div>
                                    </td>
                                    <td>TZS ${item.price.toLocaleString()}</td>
                                    <td>${item.quantity}</td>
                                    <td class="text-right">TZS ${item.total.toLocaleString()}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                        <tfoot>
                            <tr>
                                <td colspan="3" class="text-right">Subtotal:</td>
                                <td class="text-right">TZS ${parseFloat(cartSubtotal.textContent.replace(/,/g, '')).toLocaleString()}</td>
                            </tr>
                            <tr>
                                <td colspan="3" class="text-right">Discount:</td>
                                <td class="text-right">${currentDiscount.type === 'percentage' ? currentDiscount.value + '%' : 'TZS ' + parseFloat(cartDiscount.textContent.replace(/,/g, '')).toLocaleString()}</td>
                            </tr>
                            <tr class="total-row">
                                <td colspan="3" class="text-right">Total:</td>
                                <td class="text-right">TZS ${totalAmount.toLocaleString()}</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
                
                <div class="invoice-footer">
                    <p>Thank you for your business!</p>
                    <p>For any queries regarding this invoice, please contact us.</p>
                    <div class="no-print">
                        <hr>
                        <button onclick="window.print()">Print Invoice</button>
                        <button onclick="window.close()">Close</button>
                    </div>
                </div>
            </body>
            </html>
        `);
        invoiceWindow.document.close();
    }
});