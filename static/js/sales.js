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
    loadAllProducts(); // Load all products initially

    // Event Listeners

    // Barcode scanner
    startScanBtn.addEventListener('click', startScanner);
    cancelScanBtn.addEventListener('click', stopScanner);

    // Product search
    const refreshProductsBtn = document.getElementById('refreshProductsBtn');
    
    searchProductsBtn.addEventListener('click', searchProducts);
    refreshProductsBtn.addEventListener('click', function() {
        console.log('Refreshing products...');
        productSearchInput.value = '';
        loadAllProducts();
    });
    
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
    
    // Split Payment Features
    const splitPaymentBtn = document.getElementById('splitPaymentBtn');
    const splitPaymentModal = document.getElementById('splitPaymentModal');
    
    if (splitPaymentBtn) {
        splitPaymentBtn.addEventListener('click', initializeSplitPayment);
    }

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

        // Show loading state
        productResultsTable.innerHTML = '<tr><td colspan="6" class="text-center"><div class="spinner-border spinner-border-sm text-secondary" role="status"></div> Searching...</td></tr>';

        // If no query, load all products
        const searchUrl = query ? `/api/inventory?search=${encodeURIComponent(query)}` : '/api/inventory';
        
        console.log('Searching products with URL:', searchUrl);

        // Make API request to search inventory
        fetch(searchUrl)
            .then(response => {
                console.log('Search response status:', response.status);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(items => {
                console.log('Search results received:', items);
                searchResults = items;
                displaySearchResults(items);
            })
            .catch(error => {
                console.error('Error searching products:', error);
                productResultsTable.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Error searching products. Please try again.</td></tr>';
            });
    }

    // Load all products on page load
    function loadAllProducts() {
        console.log('Loading all products...');
        searchProducts();
    }

    function displaySearchResults(items) {
        console.log('Displaying search results:', items);
        
        if (items.length === 0) {
            productResultsTable.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No products found</td></tr>';
            return;
        }

        let html = '';

        items.forEach(item => {
            // Determine which price to display based on the sale type
            const displayPrice = saleType === 'retail' 
                ? (item.selling_price_retail || item.price || 0)
                : (item.selling_price_wholesale || item.price || 0);

            // Only show items with stock
            if (item.quantity > 0) {
                html += `
                    <tr>
                        <td>
                            <div class="fw-bold">${item.name}</div>
                            <div class="small text-muted">${item.description || ''}</div>
                        </td>
                        <td>${item.sku || 'N/A'}</td>
                        <td>
                            <span class="badge bg-secondary">${item.category || 'Uncategorized'}</span>
                        </td>
                        <td><span class="currency-symbol">TZS</span> ${displayPrice.toLocaleString()}</td>
                        <td>
                            <span class="badge ${item.quantity <= 10 ? 'bg-warning' : 'bg-success'}">${item.quantity}</span>
                        </td>
                        <td>
                            <button class="btn btn-sm btn-primary add-to-cart" data-id="${item.id}" title="Add to cart">
                                <i class="fas fa-plus"></i>
                            </button>
                        </td>
                    </tr>
                `;
            }
        });

        if (html === '') {
            productResultsTable.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No products with stock found</td></tr>';
        } else {
            productResultsTable.innerHTML = html;
        }

        // Add event listeners to Add buttons
        document.querySelectorAll('.add-to-cart').forEach(button => {
            button.addEventListener('click', function() {
                const itemId = this.getAttribute('data-id');
                console.log('Adding item to cart:', itemId);
                addToCart(itemId);
            });
        });
    }

    // Cart Functions
    function addToCart(itemId) {
        console.log('Adding to cart, item ID:', itemId);
        console.log('Current search results:', searchResults);
        
        const item = searchResults.find(item => item.id == itemId);

        if (!item) {
            console.error('Item not found in search results:', itemId);
            alert('Item not found. Please search again.');
            return;
        }

        console.log('Found item:', item);

        // Check stock availability
        if (item.quantity <= 0) {
            alert('This item is out of stock');
            return;
        }

        // Check if the item is already in the cart
        const existingItemIndex = cart.findIndex(cartItem => cartItem.id == itemId);

        if (existingItemIndex >= 0) {
            // Check if we can add more quantity
            const currentCartQty = cart[existingItemIndex].quantity;
            if (currentCartQty >= item.quantity) {
                alert('Cannot add more items. Insufficient stock.');
                return;
            }
            
            // Increment quantity if already in cart
            cart[existingItemIndex].quantity += 1;
            cart[existingItemIndex].total = cart[existingItemIndex].price * cart[existingItemIndex].quantity;
        } else {
            // Add new item to cart
            const price = saleType === 'retail' 
                ? (item.selling_price_retail || item.price || 0) 
                : (item.selling_price_wholesale || item.price || 0);

            if (price <= 0) {
                alert('This item has no valid price set');
                return;
            }

            cart.push({
                id: item.id,
                name: item.name,
                sku: item.sku,
                price: price,
                selling_price_retail: item.selling_price_retail || item.price || 0,
                selling_price_wholesale: item.selling_price_wholesale || item.price || 0,
                quantity: 1,
                unit_type: item.unit_type || 'quantity',
                total: price,
                max_quantity: item.quantity // Track available stock
            });
        }

        console.log('Cart after adding item:', cart);
        updateCartDisplay();
        
        // Show success feedback
        const button = document.querySelector(`[data-id="${itemId}"]`);
        if (button) {
            const originalText = button.innerHTML;
            button.innerHTML = '<i class="fas fa-check"></i>';
            button.classList.remove('btn-primary');
            button.classList.add('btn-success');
            
            setTimeout(() => {
                button.innerHTML = originalText;
                button.classList.remove('btn-success');
                button.classList.add('btn-primary');
            }, 1000);
        }
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
        console.log('Complete transaction button clicked');
        
        if (cart.length === 0) {
            alert('Please add items to the cart before completing transaction');
            return;
        }

        const customerName = document.getElementById('customerName').value || 'Walk-in Customer';
        const customerPhone = document.getElementById('customerPhone').value || '';
        const payment = document.getElementById('paymentMethod').value;
        const amount = parseFloat(document.getElementById('paymentAmount').value) || 0;
        const notes = document.getElementById('saleNotes').value || '';

        console.log('Payment amount entered:', amount);
        console.log('Current cart:', cart);

        let mobileInfo = {};
        if (payment === 'mobile_money') {
            const providerElement = document.getElementById('mobileProvider');
            const referenceElement = document.getElementById('transactionReference');
            
            if (providerElement && referenceElement) {
                mobileInfo = {
                    provider: providerElement.value,
                    reference: referenceElement.value
                };
            }
        }

        const totalAmount = parseFloat(cartTotal.textContent.replace(/,/g, ''));
        console.log('Total amount:', totalAmount, 'Payment amount:', amount);

        if (amount <= 0) {
            alert('Please enter a valid payment amount');
            document.getElementById('paymentAmount').focus();
            return;
        }

        if (amount < totalAmount) {
            const confirmation = confirm(`Payment amount (TZS ${amount.toLocaleString()}) is less than the total (TZS ${totalAmount.toLocaleString()}). Do you want to continue with partial payment?`);
            if (!confirmation) {
                return;
            }
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
                change: Math.max(0, amount - totalAmount),
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

        console.log('Transaction data to send:', transaction);

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
            console.log('Transaction response status:', response.status);
            if (!response.ok) {
                return response.text().then(text => {
                    throw new Error(`HTTP error! Status: ${response.status}, Response: ${text}`);
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('Transaction completed successfully:', data);
            
            // Show success message with transaction details
            const changeAmount = Math.max(0, amount - totalAmount);
            let successMessage = 'Transaction completed successfully!';
            if (changeAmount > 0) {
                successMessage += `\n\nChange to give: TZS ${changeAmount.toLocaleString()}`;
            }
            alert(successMessage);

            // Clear the cart and reset form
            clearCart();
            document.getElementById('checkoutForm').reset();
            
            // Reset payment amount to 0
            document.getElementById('paymentAmount').value = '';

            // Reset button
            completeTransactionBtn.disabled = false;
            completeTransactionBtn.innerHTML = '<i class="fas fa-check-circle me-1"></i> Complete Transaction';
            
            // Refresh products to update stock quantities
            if (typeof loadAllProducts === 'function') {
                loadAllProducts();
            }
        })
        .catch(error => {
            console.error('Error completing transaction:', error);
            alert(`Failed to complete transaction: ${error.message}. Please try again.`);

            // Reset button
            completeTransactionBtn.disabled = false;
            completeTransactionBtn.innerHTML = '<i class="fas fa-check-circle me-1"></i> Complete Transaction';
        });
    }

    // Split Payment Management
    let splitPayments = [];
    
    function initializeSplitPayment() {
        const totalAmount = parseFloat(cartTotal.textContent.replace(/,/g, ''));
        splitPayments = [];
        updateSplitPaymentDisplay();
        
        // Set remaining amount to total
        const remainingAmountDisplay = document.getElementById('remainingAmount');
        if (remainingAmountDisplay) {
            remainingAmountDisplay.textContent = `TZS ${totalAmount.toLocaleString()}`;
        }
        
        // Show split payment modal
        const modal = new bootstrap.Modal(splitPaymentModal);
        modal.show();
    }
    
    function addSplitPayment() {
        const method = document.getElementById('splitPaymentMethod').value;
        const amount = parseFloat(document.getElementById('splitPaymentAmount').value);
        const reference = document.getElementById('splitPaymentReference').value;
        
        if (!amount || amount <= 0) {
            alert('Please enter a valid payment amount');
            return;
        }
        
        const totalAmount = parseFloat(cartTotal.textContent.replace(/,/g, ''));
        const currentTotal = splitPayments.reduce((sum, payment) => sum + payment.amount, 0);
        
        if (currentTotal + amount > totalAmount) {
            alert('Payment amount exceeds remaining balance');
            return;
        }
        
        splitPayments.push({
            method: method,
            amount: amount,
            reference: reference || '',
            timestamp: new Date().toISOString()
        });
        
        updateSplitPaymentDisplay();
        
        // Clear form
        document.getElementById('splitPaymentAmount').value = '';
        document.getElementById('splitPaymentReference').value = '';
    }
    
    function updateSplitPaymentDisplay() {
        const totalAmount = parseFloat(cartTotal.textContent.replace(/,/g, ''));
        const paidAmount = splitPayments.reduce((sum, payment) => sum + payment.amount, 0);
        const remainingAmount = totalAmount - paidAmount;
        
        const splitPaymentsList = document.getElementById('splitPaymentsList');
        const remainingAmountDisplay = document.getElementById('remainingAmount');
        
        // Update payments list
        splitPaymentsList.innerHTML = '';
        splitPayments.forEach((payment, index) => {
            const paymentRow = document.createElement('div');
            paymentRow.className = 'row mb-2';
            paymentRow.innerHTML = `
                <div class="col-4">${payment.method}</div>
                <div class="col-4">TZS ${payment.amount.toLocaleString()}</div>
                <div class="col-4">
                    <button type="button" class="btn btn-sm btn-danger" onclick="removeSplitPayment(${index})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
            splitPaymentsList.appendChild(paymentRow);
        });
        
        // Update remaining amount
        remainingAmountDisplay.textContent = `TZS ${remainingAmount.toLocaleString()}`;
        
        // Enable/disable complete button
        const completeSplitBtn = document.getElementById('completeSplitPayment');
        completeSplitBtn.disabled = remainingAmount > 0;
    }
    
    function removeSplitPayment(index) {
        splitPayments.splice(index, 1);
        updateSplitPaymentDisplay();
    }
    
    function completeSplitPayment() {
        const totalAmount = parseFloat(cartTotal.textContent.replace(/,/g, ''));
        const paidAmount = splitPayments.reduce((sum, payment) => sum + payment.amount, 0);
        
        if (paidAmount < totalAmount) {
            alert('Payment amount is less than total. Please add more payments.');
            return;
        }
        
        // Process the transaction with split payments
        processSplitPaymentTransaction();
        
        // Close modal
        const modal = bootstrap.Modal.getInstance(splitPaymentModal);
        modal.hide();
    }
    
    function processSplitPaymentTransaction() {
        const customerName = document.getElementById('customerName').value || 'Walk-in Customer';
        const customerPhone = document.getElementById('customerPhone').value || '';
        const notes = document.getElementById('saleNotes').value || '';
        const totalAmount = parseFloat(cartTotal.textContent.replace(/,/g, ''));
        
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
                method: 'split',
                amount: totalAmount,
                change: 0,
                split_payments: splitPayments
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
        
        // Send to server
        fetch('/api/sales', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(transaction)
        })
        .then(response => response.json())
        .then(data => {
            alert('Split payment transaction completed successfully!');
            clearCart();
            document.getElementById('checkoutForm').reset();
            splitPayments = [];
            loadAllProducts();
        })
        .catch(error => {
            console.error('Error processing split payment:', error);
            alert('Failed to process split payment transaction');
        });
    }

    function createInvoice() {
        if (cart.length === 0) {
            alert('Please add items to the cart before creating an invoice');
            return;
        }

        // Get shop details
        fetch('/api/shop/details')
            .then(response => response.json())
            .then(shopData => {
                generatePrintableInvoice(shopData.user || {});
            })
            .catch(error => {
                console.error('Error getting shop details:', error);
                generatePrintableInvoice({});
            });
    }

    function generatePrintableInvoice(shopInfo) {
        const customerName = document.getElementById('customerName').value || 'Walk-in Customer';
        const customerPhone = document.getElementById('customerPhone').value || '';
        const totalAmount = parseFloat(cartTotal.textContent.replace(/,/g, ''));
        const invoiceNumber = `INV-${Date.now().toString().substring(6)}`;

        // Create a printable invoice in a new window
        const invoiceWindow = window.open('', '_blank');
        invoiceWindow.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Invoice - ${invoiceNumber}</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {
                        font-family: 'Arial', sans-serif;
                        line-height: 1.4;
                        color: #333;
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 20px;
                        font-size: 14px;
                    }
                    .invoice-header {
                        text-align: center;
                        margin-bottom: 30px;
                        border-bottom: 2px solid #4B0082;
                        padding-bottom: 20px;
                    }
                    .shop-name {
                        color: #4B0082;
                        font-size: 28px;
                        font-weight: bold;
                        margin-bottom: 5px;
                    }
                    .invoice-title {
                        font-size: 24px;
                        color: #666;
                        margin: 10px 0;
                    }
                    .invoice-meta {
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 20px;
                        margin-bottom: 30px;
                    }
                    .customer-info, .invoice-info {
                        background: #f8f9fa;
                        padding: 15px;
                        border-radius: 8px;
                    }
                    table {
                        width: 100%;
                        border-collapse: collapse;
                        margin-bottom: 20px;
                        border: 1px solid #ddd;
                    }
                    th, td {
                        padding: 12px 8px;
                        border-bottom: 1px solid #eee;
                        text-align: left;
                    }
                    th {
                        background-color: #4B0082;
                        color: white;
                        font-weight: bold;
                    }
                    .text-right {
                        text-align: right;
                    }
                    .text-center {
                        text-align: center;
                    }
                    .total-section {
                        background: #f8f9fa;
                        padding: 15px;
                        border-radius: 8px;
                        margin-top: 20px;
                    }
                    .total-row {
                        font-weight: bold;
                        font-size: 16px;
                        background: #4B0082 !important;
                        color: white !important;
                    }
                    .invoice-footer {
                        margin-top: 40px;
                        border-top: 1px solid #ddd;
                        padding-top: 20px;
                        text-align: center;
                        font-size: 12px;
                        color: #666;
                    }
                    .qr-code {
                        width: 100px;
                        height: 100px;
                        border: 1px solid #ddd;
                        display: inline-block;
                        text-align: center;
                        line-height: 100px;
                        margin: 10px;
                    }
                    @media print {
                        body {
                            padding: 0;
                            font-size: 12px;
                        }
                        .no-print {
                            display: none;
                        }
                        .invoice-header {
                            border-bottom: 2px solid #000;
                        }
                        th {
                            background-color: #000 !important;
                            -webkit-print-color-adjust: exact;
                        }
                        .total-row {
                            background-color: #000 !important;
                            -webkit-print-color-adjust: exact;
                        }
                    }
                    .action-buttons {
                        text-align: center;
                        margin: 20px 0;
                    }
                    .action-buttons button {
                        margin: 0 10px;
                        padding: 10px 20px;
                        border: none;
                        border-radius: 5px;
                        cursor: pointer;
                        font-size: 14px;
                    }
                    .print-btn {
                        background: #4B0082;
                        color: white;
                    }
                    .close-btn {
                        background: #dc3545;
                        color: white;
                    }
                    .email-btn {
                        background: #28a745;
                        color: white;
                    }
                </style>
            </head>
            <body>
                <div class="invoice-header">
                    <div class="shop-name">${shopInfo.shop_name || 'Your Shop'}</div>
                    <div>Inventory Management System</div>
                    <div class="invoice-title">SALES INVOICE</div>
                </div>

                <div class="invoice-meta">
                    <div class="customer-info">
                        <h4 style="margin-top: 0; color: #4B0082;">Bill To:</h4>
                        <strong>${customerName}</strong><br>
                        ${customerPhone ? `Phone: ${customerPhone}<br>` : ''}
                        ${customerPhone ? `Email: ${document.getElementById('customerEmail')?.value || 'N/A'}` : ''}
                    </div>
                    <div class="invoice-info">
                        <h4 style="margin-top: 0; color: #4B0082;">Invoice Details:</h4>
                        <strong>Invoice #:</strong> ${invoiceNumber}<br>
                        <strong>Date:</strong> ${new Date().toLocaleDateString()}<br>
                        <strong>Time:</strong> ${new Date().toLocaleTimeString()}<br>
                        <strong>Cashier:</strong> ${shopInfo.owner_name || 'Cashier'}
                    </div>
                </div>

                <table>
                    <thead>
                        <tr>
                            <th>Item Description</th>
                            <th class="text-center">Qty</th>
                            <th class="text-right">Unit Price</th>
                            <th class="text-right">Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${cart.map(item => `
                            <tr>
                                <td>
                                    <strong>${item.name}</strong>
                                    ${item.sku ? `<br><small style="color: #666;">SKU: ${item.sku}</small>` : ''}
                                </td>
                                <td class="text-center">${item.quantity}</td>
                                <td class="text-right">TZS ${item.price.toLocaleString()}</td>
                                <td class="text-right">TZS ${item.total.toLocaleString()}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>

                <div class="total-section">
                    <table style="border: none; margin: 0;">
                        <tr>
                            <td style="border: none; width: 60%;"></td>
                            <td style="border: none; text-align: right; padding: 5px 0;">Subtotal:</td>
                            <td style="border: none; text-align: right; padding: 5px 0; font-weight: bold;">TZS ${parseFloat(cartSubtotal.textContent.replace(/,/g, '')).toLocaleString()}</td>
                        </tr>
                        ${currentDiscount.type !== 'none' ? `
                        <tr>
                            <td style="border: none;"></td>
                            <td style="border: none; text-align: right; padding: 5px 0;">Discount (${currentDiscount.type === 'percentage' ? currentDiscount.value + '%' : 'Fixed'}):</td>
                            <td style="border: none; text-align: right; padding: 5px 0; color: #dc3545;">-TZS ${parseFloat(cartDiscount.textContent.replace(/,/g, '')).toLocaleString()}</td>
                        </tr>` : ''}
                        <tr class="total-row">
                            <td style="border: none;"></td>
                            <td style="padding: 10px 0; text-align: right; background: #4B0082; color: white;">TOTAL:</td>
                            <td style="padding: 10px 0; text-align: right; background: #4B0082; color: white; font-size: 18px;">TZS ${totalAmount.toLocaleString()}</td>
                        </tr>
                    </table>
                </div>

                <div class="invoice-footer">
                    <div style="margin-bottom: 20px;">
                        <div class="qr-code">QR Code</div>
                        <p><strong>Thank you for your business!</strong></p>
                        <p>For support or inquiries, please contact us.</p>
                        <p><em>This is a computer-generated invoice.</em></p>
                    </div>
                    
                    <div class="no-print action-buttons">
                        <button class="print-btn" onclick="window.print()">
                            🖨️ Print Receipt
                        </button>
                        <button class="email-btn" onclick="emailReceipt()">
                            📧 Email Receipt
                        </button>
                        <button class="close-btn" onclick="window.close()">
                            ❌ Close
                        </button>
                    </div>
                </div>

                <script>
                    function emailReceipt() {
                        const email = prompt('Enter customer email address:');
                        if (email) {
                            // Here you would integrate with your email service
                            alert('Email functionality would be integrated here');
                        }
                    }
                </script>
            </body>
            </html>
        `);
        invoiceWindow.document.close();
    }

    // Layaway Management Functions
    function createLayaway() {
        if (cart.length === 0) {
            alert('Please add items to the cart before creating a layaway plan');
            return;
        }

        const customerName = document.getElementById('layawayCustomerName').value;
        const customerPhone = document.getElementById('layawayCustomerPhone').value;
        const downPayment = parseFloat(document.getElementById('layawayDownPayment').value) || 0;
        const installmentAmount = parseFloat(document.getElementById('layawayInstallmentAmount').value) || 0;
        const frequency = document.getElementById('layawayFrequency').value;
        const nextPaymentDate = document.getElementById('layawayNextPayment').value;
        const notes = document.getElementById('layawayNotes').value;

        if (!customerName || !customerPhone) {
            alert('Customer name and phone are required');
            return;
        }

        const totalAmount = parseFloat(cartTotal.textContent.replace(/,/g, ''));

        if (installmentAmount <= 0) {
            alert('Please enter a valid installment amount');
            return;
        }

        const layawayData = {
            customer_name: customerName,
            customer_phone: customerPhone,
            total_amount: totalAmount,
            down_payment: downPayment,
            installment_amount: installmentAmount,
            payment_frequency: frequency,
            next_payment_date: nextPaymentDate,
            items: cart.map(item => ({
                id: item.id,
                name: item.name,
                sku: item.sku,
                price: item.price,
                quantity: item.quantity,
                total: item.total
            })),
            notes: notes
        };

        fetch('/api/layaway', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(layawayData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.id) {
                alert('Layaway plan created successfully!');
                
                // Clear cart and close modal
                clearCart();
                const modal = bootstrap.Modal.getInstance(document.getElementById('layawayModal'));
                modal.hide();
                
                // Reset form
                document.getElementById('layawayCustomerName').value = '';
                document.getElementById('layawayCustomerPhone').value = '';
                document.getElementById('layawayDownPayment').value = '';
                document.getElementById('layawayInstallmentAmount').value = '';
                document.getElementById('layawayNotes').value = '';
            } else {
                alert('Error creating layaway plan: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error creating layaway plan:', error);
            alert('Failed to create layaway plan');
        });
    }

    // Update layaway summary when values change
    function updateLayawaySummary() {
        const totalAmount = parseFloat(cartTotal.textContent.replace(/,/g, ''));
        const downPayment = parseFloat(document.getElementById('layawayDownPayment').value) || 0;
        const installmentAmount = parseFloat(document.getElementById('layawayInstallmentAmount').value) || 0;
        const remainingBalance = totalAmount - downPayment;

        document.getElementById('layawayTotalAmount').textContent = `TZS ${totalAmount.toLocaleString()}`;
        document.getElementById('layawayDownPaymentDisplay').textContent = `TZS ${downPayment.toLocaleString()}`;
        document.getElementById('layawayRemainingBalance').textContent = `TZS ${remainingBalance.toLocaleString()}`;

        if (installmentAmount > 0) {
            const estimatedPayments = Math.ceil(remainingBalance / installmentAmount);
            document.getElementById('layawayEstimatedPayments').textContent = estimatedPayments;
        } else {
            document.getElementById('layawayEstimatedPayments').textContent = '0';
        }
    }

    // Add event listeners for layaway calculations
    if (document.getElementById('layawayDownPayment')) {
        document.getElementById('layawayDownPayment').addEventListener('input', updateLayawaySummary);
        document.getElementById('layawayInstallmentAmount').addEventListener('input', updateLayawaySummary);
    }
});