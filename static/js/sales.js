
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

    // Modern Success Popup Function
    function showSuccessPopup(data) {
        // Create popup HTML
        const popupHTML = `
            <div class="success-popup-overlay" id="successPopupOverlay">
                <div class="success-popup-modal">
                    <div class="success-popup-header">
                        <div class="success-icon-container">
                            <i class="fas fa-check-circle success-icon"></i>
                        </div>
                        <h3 class="success-title">Transaction Completed!</h3>
                        <p class="success-subtitle">Your sale has been processed successfully</p>
                    </div>
                    <div class="success-popup-body">
                        <div class="transaction-details">
                            <div class="detail-row">
                                <span class="detail-label">Sale Number:</span>
                                <span class="detail-value">${data.sale_number || 'N/A'}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Total Amount:</span>
                                <span class="detail-value">TZS ${(data.total_amount || 0).toLocaleString()}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Payment Method:</span>
                                <span class="detail-value">${paymentMethod ? paymentMethod.value.replace('_', ' ').toUpperCase() : 'CASH'}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Customer:</span>
                                <span class="detail-value">${document.getElementById('customerName') ? document.getElementById('customerName').value || 'Walk-in Customer' : 'Walk-in Customer'}</span>
                            </div>
                        </div>
                    </div>
                    <div class="success-popup-footer">
                        <button class="btn btn-primary success-btn" onclick="closeSuccessPopup()">
                            <i class="fas fa-thumbs-up me-2"></i>Continue Shopping
                        </button>
                        <button class="btn btn-outline-primary success-btn" onclick="printReceipt('${data.sale_number}')">
                            <i class="fas fa-print me-2"></i>Print Receipt
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Add popup to body
        document.body.insertAdjacentHTML('beforeend', popupHTML);

        // Show popup with animation
        setTimeout(() => {
            document.getElementById('successPopupOverlay').classList.add('show');
        }, 100);

        // Auto-close after 5 seconds
        setTimeout(() => {
            closeSuccessPopup();
        }, 5000);
    }

    // Close success popup
    function closeSuccessPopup() {
        const overlay = document.getElementById('successPopupOverlay');
        if (overlay) {
            overlay.classList.remove('show');
            setTimeout(() => {
                overlay.remove();
            }, 300);
        }
    }

    // Error popup function
    function showErrorPopup(message) {
        const errorPopupHTML = `
            <div class="error-popup-overlay" id="errorPopupOverlay">
                <div class="error-popup-modal">
                    <div class="error-popup-header">
                        <div class="error-icon-container">
                            <i class="fas fa-exclamation-triangle error-icon"></i>
                        </div>
                        <h3 class="error-title">Transaction Error</h3>
                    </div>
                    <div class="error-popup-body">
                        <p class="error-message">${message}</p>
                    </div>
                    <div class="error-popup-footer">
                        <button class="btn btn-danger error-btn" onclick="closeErrorPopup()">
                            <i class="fas fa-times me-2"></i>Close
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', errorPopupHTML);

        setTimeout(() => {
            document.getElementById('errorPopupOverlay').classList.add('show');
        }, 100);
    }

    // Close error popup
    function closeErrorPopup() {
        const overlay = document.getElementById('errorPopupOverlay');
        if (overlay) {
            overlay.classList.remove('show');
            setTimeout(() => {
                overlay.remove();
            }, 300);
        }
    }

    // Print receipt function
    function printReceipt(saleNumber) {
        // Create a simple receipt
        const customerName = document.getElementById('customerName') ? document.getElementById('customerName').value || 'Walk-in Customer' : 'Walk-in Customer';
        const totalAmount = cartTotal ? parseFloat(cartTotal.textContent.replace(/,/g, '')) : 0;

        const receiptWindow = window.open('', '_blank');
        receiptWindow.document.write(`<!DOCTYPE html>
<html>
<head>
    <title>Receipt - ${saleNumber}</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 300px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 20px; border-bottom: 2px solid #333; padding-bottom: 10px; }
        .detail { display: flex; justify-content: space-between; margin: 5px 0; }
        .total { font-weight: bold; border-top: 1px solid #333; padding-top: 10px; }
        @media print { body { margin: 0; } }
    </style>
</head>
<body>
    <div class="header">
        <h2>RECEIPT</h2>
        <p>${saleNumber}</p>
        <p>${new Date().toLocaleDateString()}</p>
    </div>
    <div class="detail">
        <span>Customer:</span>
        <span>${customerName}</span>
    </div>
    <div class="detail">
        <span>Payment:</span>
        <span>${paymentMethod ? paymentMethod.value.replace('_', ' ').toUpperCase() : 'CASH'}</span>
    </div>
    <div class="detail total">
        <span>Total:</span>
        <span>TZS ${totalAmount.toLocaleString()}</span>
    </div>
    <div style="text-align: center; margin-top: 20px;">
        <p>Thank you for your business!</p>
        <button onclick="window.print()">Print</button>
        <button onclick="window.close()">Close</button>
    </div>
</body>
</html>`);
        receiptWindow.document.close();

        // Close success popup
        closeSuccessPopup();
    }

    // Event Listeners

    // Barcode scanner
    if (startScanBtn) {
        startScanBtn.addEventListener('click', startScanner);
    }
    if (cancelScanBtn) {
        cancelScanBtn.addEventListener('click', stopScanner);
    }

    // Product search
    if (searchProductsBtn) {
        searchProductsBtn.addEventListener('click', searchProducts);
    }
    if (productSearchInput) {
        productSearchInput.addEventListener('keyup', function(e) {
            if (e.key === 'Enter') {
                searchProducts();
            }
        });
    }

    // Show all products button
    const showAllProductsBtn = document.getElementById('showAllProductsBtn');
    if (showAllProductsBtn) {
        showAllProductsBtn.addEventListener('click', loadAllProducts);
    }

    // Sale type selection
    if (saleTypeSelector) {
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
    }

    // Unit type selection
    const unitTypeSelector = document.getElementById('unitTypeSelector');
    if (unitTypeSelector) {
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
    }

    // Cart management
    if (clearCartBtn) {
        clearCartBtn.addEventListener('click', clearCart);
    }

    // Payment method toggle
    if (paymentMethod) {
        paymentMethod.addEventListener('change', function() {
            // Hide all payment-specific fields first
            if (mobileMoneyFields) {
                mobileMoneyFields.classList.add('d-none');
            }
            const installmentFields = document.getElementById('installmentFields');
            if (installmentFields) {
                installmentFields.classList.add('d-none');
            }

            if (this.value === 'mobile_money') {
                if (mobileMoneyFields) {
                    mobileMoneyFields.classList.remove('d-none');
                }
            } else if (this.value === 'installment') {
                // Show installment customer modal immediately
                showInstallmentCustomerModal();
            }
        });
    }

    // Set payment amount to match cart total when cart changes
    if (paymentAmount) {
        paymentAmount.addEventListener('focus', function() {
            const totalAmount = parseFloat(cartTotal.textContent.replace(/,/g, '')) || 0;
            if (totalAmount > 0) {
                this.value = totalAmount;
            }
        });
    }

    // Checkout
    if (completeTransactionBtn) {
        completeTransactionBtn.addEventListener('click', completeTransaction);
    }
    if (createInvoiceBtn) {
        createInvoiceBtn.addEventListener('click', createInvoice);
    }

    // Discount application
    if (applyDiscountModalBtn) {
        applyDiscountModalBtn.addEventListener('click', applyDiscount);
    }

    // Barcode Scanner Functions
    function startScanner() {
        if (scannerContainer) {
            scannerContainer.classList.remove('d-none');
        }
        if (scanFeedback) {
            scanFeedback.textContent = 'Initializing camera...';
        }

        if (!codeReader) {
            codeReader = new ZXing.BrowserMultiFormatReader();
        }

        codeReader.listVideoInputDevices()
            .then((videoInputDevices) => {
                if (videoInputDevices.length === 0) {
                    if (scanFeedback) {
                        scanFeedback.textContent = 'No camera detected';
                    }
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
                if (scanFeedback) {
                    scanFeedback.textContent = 'Camera access denied or error';
                }
            });
    }

    function startDecoding(deviceId) {
        codeReader.decodeFromVideoDevice(deviceId, videoElement, (result, err) => {
            if (result) {
                // Successfully scanned a barcode
                if (scanFeedback) {
                    scanFeedback.textContent = `Scanned: ${result.text}`;
                }

                // Stop scanning
                stopScanner();

                // Search for the product with this barcode/SKU
                if (productSearchInput) {
                    productSearchInput.value = result.text;
                }
                searchProducts();
            }

            if (err && !(err instanceof ZXing.NotFoundException)) {
                console.error('Scanning error:', err);
                if (scanFeedback) {
                    scanFeedback.textContent = 'Error during scanning';
                }
            }
        });

        if (scanFeedback) {
            scanFeedback.textContent = 'Position barcode in the center';
        }
    }

    function stopScanner() {
        if (codeReader) {
            codeReader.reset();
            if (scannerContainer) {
                scannerContainer.classList.add('d-none');
            }
        }
    }

    // Product Search Functions
    function searchProducts() {
        const query = productSearchInput ? productSearchInput.value.trim() : '';

        // Show loading state
        if (productResultsTable) {
            productResultsTable.innerHTML = '<tr><td colspan="6" class="text-center"><div class="spinner-border spinner-border-sm text-secondary" role="status"></div> Searching...</td></tr>';
        }

        // Make API request to search inventory (empty query returns all items)
        const searchUrl = query ? `/api/inventory?search=${encodeURIComponent(query)}` : '/api/inventory';

        fetch(searchUrl, {
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json'
            }
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(items => {
                console.log('Products loaded:', items);
                searchResults = items;
                displaySearchResults(items);
            })
            .catch(error => {
                console.error('Error searching products:', error);
                if (productResultsTable) {
                    productResultsTable.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Error searching products. Please try again.</td></tr>';
                }
            });
    }

    // Function to load all products
    function loadAllProducts() {
        if (productSearchInput) {
            productSearchInput.value = ''; // Clear search input
        }
        searchProducts(); // This will now load all products since query is empty
    }

    function displaySearchResults(items) {
        if (!productResultsTable) return;

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
        if (!cartTableBody || !cartCount || !cartSubtotal || !cartTotal) return;

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
                if (cartDiscountType) cartDiscountType.textContent = currentDiscount.value + '%';
                if (cartDiscount) cartDiscount.textContent = discountAmount.toLocaleString();
                finalTotal = subtotal - discountAmount;
            } else if (currentDiscount.type === 'fixed') {
                if (cartDiscountType) cartDiscountType.textContent = 'TZS';
                if (cartDiscount) cartDiscount.textContent = currentDiscount.value.toLocaleString();
                finalTotal = subtotal - currentDiscount.value;
            }
        } else {
            if (cartDiscountType) cartDiscountType.textContent = '-';
            if (cartDiscount) cartDiscount.textContent = '0';
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
        if (!discountType || !discountValue) return;

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

        const customerName = document.getElementById('customerName') ? document.getElementById('customerName').value || 'Walk-in Customer' : 'Walk-in Customer';
        const customerPhone = document.getElementById('customerPhone') ? document.getElementById('customerPhone').value || '' : '';
        const payment = paymentMethod ? paymentMethod.value : 'cash';
        const amount = paymentAmount ? parseFloat(paymentAmount.value) || 0 : 0;
        const notes = document.getElementById('saleNotes') ? document.getElementById('saleNotes').value || '' : '';

        let mobileInfo = {};
        let installmentInfo = {};

        if (payment === 'mobile_money') {
            const mobileProvider = document.getElementById('mobileProvider');
            const transactionReference = document.getElementById('transactionReference');
            mobileInfo = {
                provider: mobileProvider ? mobileProvider.value : '',
                reference: transactionReference ? transactionReference.value : ''
            };
        } else if (payment === 'installment') {
            // Validate installment customer data
            if (!installmentCustomerData) {
                alert('Please fill in customer information for installment sales');
                showInstallmentCustomerModal();
                return;
            }

            // For installment sales, we'll create the installment sale directly
            if (cart.length !== 1) {
                alert('Installment sales currently support only one item at a time');
                return;
            }

            const installmentData = {
                customer_id: installmentCustomerData.customer_id,
                item_id: cart[0].id,
                quantity: cart[0].quantity,
                total_amount: totalAmount,
                down_payment: installmentCustomerData.installment_plan.down_payment,
                number_of_installments: installmentCustomerData.installment_plan.period_months,
                start_date: new Date().toISOString().split('T')[0],
                agreement_signed: true,
                notes: notes
            };

            // Send directly to installment API
            fetch('/api/installment-sales', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(installmentData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show modern success popup
                    showSuccessPopup({
                        sale_number: data.sale_number,
                        total_amount: totalAmount
                    });

                    // Clear the cart and reset form
                    cart = [];
                    installmentCustomerData = null;
                    updateCartDisplay();
                    const checkoutForm = document.getElementById('checkoutForm');
                    if (checkoutForm) {
                        checkoutForm.reset();
                    }

                    // Reset payment fields
                    if (paymentAmount) {
                        paymentAmount.value = '';
                    }
                    if (mobileMoneyFields) {
                        mobileMoneyFields.classList.add('d-none');
                    }
                    const installmentFields = document.getElementById('installmentFields');
                    if (installmentFields) {
                        installmentFields.classList.add('d-none');
                    }
                } else {
                    throw new Error(data.error || 'Installment sale creation failed');
                }
            })
            .catch(error => {
                console.error('Error creating installment sale:', error);
                showErrorPopup(`Installment sale failed: ${error.message}`);
            })
            .finally(() => {
                // Reset button
                if (completeTransactionBtn) {
                    completeTransactionBtn.disabled = false;
                    completeTransactionBtn.innerHTML = '<i class="fas fa-check-circle me-1"></i> Complete Transaction';
                }
            });
            
            return; // Exit early for installment sales
        }

        const totalAmount = parseFloat(cartTotal.textContent.replace(/,/g, ''));

        // Validate payment amount
        if (payment === 'installment') {
            if (amount < totalAmount * 0.1) { // Minimum 10% down payment
                alert('Down payment should be at least 10% of the total amount');
                return;
            }
        } else if (payment !== 'credit' && amount < totalAmount) {
            alert('Payment amount is less than the total');
            return;
        }

        // Prepare transaction data
        const transaction = {
            customer: {
                name: customerName,
                phone: customerPhone,
                address: payment === 'installment' ? installmentCustomerData?.address : null
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
                change: payment === 'installment' ? 0 : amount - totalAmount,
                mobile_info: payment === 'mobile_money' ? mobileInfo : null,
                installment_info: payment === 'installment' ? installmentInfo : null
            },
            sale_type: saleType,
            subtotal: parseFloat(cartSubtotal.textContent.replace(/,/g, '')),
            discount: {
                type: currentDiscount.type,
                value: currentDiscount.value,
                amount: cartDiscount ? parseFloat(cartDiscount.textContent.replace(/,/g, '')) : 0
            },
            total: totalAmount,
            notes: notes,
            date: new Date().toISOString()
        };

        // Show loading state
        if (completeTransactionBtn) {
            completeTransactionBtn.disabled = true;
            completeTransactionBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
        }

        // Send transaction data to the server
        fetch('/api/sales', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin',
            body: JSON.stringify(transaction)
        })
        .then(response => {
            console.log('Transaction response status:', response.status);

            if (!response.ok) {
                // If it's a redirect (like 302), log the issue
                if (response.status === 302) {
                    console.error('Transaction failed - user not authenticated');
                    throw new Error('Authentication required. Please log in again.');
                }
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Transaction response data:', data);

            if (data.success) {
                // Show modern success popup
                showSuccessPopup(data);

                // Clear the cart and reset form
                cart = [];
                installmentCustomerData = null;
                updateCartDisplay();
                const checkoutForm = document.getElementById('checkoutForm');
                if (checkoutForm) {
                    checkoutForm.reset();
                }

                // Reset payment fields
                if (paymentAmount) {
                    paymentAmount.value = '';
                }
                if (mobileMoneyFields) {
                    mobileMoneyFields.classList.add('d-none');
                }
                const installmentFields = document.getElementById('installmentFields');
                if (installmentFields) {
                    installmentFields.classList.add('d-none');
                }
            } else {
                throw new Error(data.error || 'Transaction failed');
            }

            // Reset button
            if (completeTransactionBtn) {
                completeTransactionBtn.disabled = false;
                completeTransactionBtn.innerHTML = '<i class="fas fa-check-circle me-1"></i> Complete Transaction';
            }
        })
        .catch(error => {
            console.error('Error completing transaction:', error);

            // Show more specific error message
            if (error.message.includes('Authentication required')) {
                showErrorPopup('Your session has expired. Please log in again.');
                setTimeout(() => {
                    window.location.href = '/login';
                }, 2000);
            } else if (error.message.includes('Failed to fetch')) {
                showErrorPopup('Network error. Please check your connection and try again.');
            } else {
                showErrorPopup(`Transaction failed: ${error.message}`);
            }

            // Reset button
            if (completeTransactionBtn) {
                completeTransactionBtn.disabled = false;
                completeTransactionBtn.innerHTML = '<i class="fas fa-check-circle me-1"></i> Complete Transaction';
            }
        });
    }

    function createInvoice() {
        if (cart.length === 0) {
            alert('Please add items to the cart before creating an invoice');
            return;
        }

        // Prepare invoice data
        const customerName = document.getElementById('customerName') ? document.getElementById('customerName').value || 'Walk-in Customer' : 'Walk-in Customer';
        const customerPhone = document.getElementById('customerPhone') ? document.getElementById('customerPhone').value || '' : '';
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
                                <td class="text-right">${currentDiscount.type === 'percentage' ? currentDiscount.value + '%' : 'TZS ' + (cartDiscount ? parseFloat(cartDiscount.textContent.replace(/,/g, '')).toLocaleString() : '0')}</td>
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

    // Make functions global for popup access
    window.closeSuccessPopup = closeSuccessPopup;
    window.closeErrorPopup = closeErrorPopup;
    window.printReceipt = printReceipt;

    // Enhanced features
    function switchCamera() {
        // Implementation for switching between front/back camera
        if (codeReader && selectedDeviceId) {
            stopScanner();
            startScanner();
        }
    }

    function holdTransaction() {
        // Save current cart state for later
        const heldTransaction = {
            cart: [...cart],
            customer: {
                name: document.getElementById('customerName').value,
                phone: document.getElementById('customerPhone').value
            },
            timestamp: new Date().toISOString()
        };
        
        localStorage.setItem('heldTransaction', JSON.stringify(heldTransaction));
        clearCart();
        
        // Show confirmation
        const alert = document.createElement('div');
        alert.className = 'alert alert-info alert-dismissible fade show position-fixed';
        alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alert.innerHTML = `
            <i class="fas fa-pause me-2"></i>
            Transaction held successfully
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alert);
        
        setTimeout(() => {
            if (alert.parentNode) alert.remove();
        }, 3000);
    }

    function loadHeldTransaction() {
        const held = localStorage.getItem('heldTransaction');
        if (held) {
            const transaction = JSON.parse(held);
            cart = transaction.cart;
            updateCartDisplay();
            
            if (transaction.customer.name) {
                document.getElementById('customerName').value = transaction.customer.name;
            }
            if (transaction.customer.phone) {
                document.getElementById('customerPhone').value = transaction.customer.phone;
            }
            
            localStorage.removeItem('heldTransaction');
        }
    }

    // Auto-save cart to prevent data loss
    function autoSaveCart() {
        if (cart.length > 0) {
            localStorage.setItem('autoSaveCart', JSON.stringify({
                cart: cart,
                timestamp: new Date().toISOString()
            }));
        } else {
            localStorage.removeItem('autoSaveCart');
        }
    }

    function loadAutoSavedCart() {
        const saved = localStorage.getItem('autoSaveCart');
        if (saved) {
            const data = JSON.parse(saved);
            // Only load if saved within last hour
            const hourAgo = new Date(Date.now() - 60 * 60 * 1000);
            if (new Date(data.timestamp) > hourAgo) {
                cart = data.cart;
                updateCartDisplay();
            } else {
                localStorage.removeItem('autoSaveCart');
            }
        }
    }

    // Auto-save cart on changes
    const originalUpdateCartDisplay = updateCartDisplay;
    updateCartDisplay = function() {
        originalUpdateCartDisplay.call(this);
        autoSaveCart();
    };

    // Make functions global
    window.switchCamera = switchCamera;
    window.holdTransaction = holdTransaction;
    window.loadHeldTransaction = loadHeldTransaction;

    // Load auto-saved cart and held transactions on page load
    loadAutoSavedCart();
    
    // Check for held transactions
    if (localStorage.getItem('heldTransaction')) {
        const loadBtn = document.createElement('button');
        loadBtn.className = 'btn btn-warning btn-sm position-fixed';
        loadBtn.style.cssText = 'top: 20px; left: 20px; z-index: 9999;';
        loadBtn.innerHTML = '<i class="fas fa-play me-1"></i> Load Held Transaction';
        loadBtn.onclick = loadHeldTransaction;
        document.body.appendChild(loadBtn);
    }

    // Initialize installment customer modal
    initializeInstallmentCustomerModal();

    // Initialize search on page load
    if (productSearchInput) {
        loadAllProducts();
    }

    // Initialize completed transactions tab
    initializeCompletedTransactions();
});

// Installment Customer Modal Functions
let installmentCustomerData = null;

function initializeInstallmentCustomerModal() {
    // Event listeners for installment modal
    const saveInstallmentCustomerBtn = document.getElementById('saveInstallmentCustomer');
    const installmentDownPaymentInput = document.getElementById('installmentDownPayment');
    const installmentPeriodSelect = document.getElementById('installmentPeriod');
    const existingCustomerSelect = document.getElementById('installmentExistingCustomer');
    const newCustomerToggle = document.getElementById('installmentNewCustomerToggle');

    if (saveInstallmentCustomerBtn) {
        saveInstallmentCustomerBtn.addEventListener('click', saveInstallmentCustomerInfo);
    }

    if (installmentDownPaymentInput) {
        installmentDownPaymentInput.addEventListener('input', updateInstallmentSummary);
    }

    if (installmentPeriodSelect) {
        installmentPeriodSelect.addEventListener('change', updateInstallmentSummary);
    }

    // Handle existing customer selection
    if (existingCustomerSelect) {
        existingCustomerSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            if (selectedOption.value && selectedOption.dataset.customerData) {
                const customerData = JSON.parse(selectedOption.dataset.customerData);
                populateInstallmentCustomerForm(customerData);
                
                // Hide new customer fields when existing customer is selected
                toggleInstallmentCustomerFields(false);
            } else {
                // Clear form when no customer is selected
                clearInstallmentCustomerForm();
            }
        });
    }

    // Handle new customer toggle
    if (newCustomerToggle) {
        newCustomerToggle.addEventListener('change', function() {
            if (this.checked) {
                // Clear existing customer selection
                if (existingCustomerSelect) {
                    existingCustomerSelect.value = '';
                }
                clearInstallmentCustomerForm();
                toggleInstallmentCustomerFields(true);
            } else {
                toggleInstallmentCustomerFields(false);
            }
        });
    }
}

function populateInstallmentCustomerForm(customerData) {
    // Populate form fields with existing customer data
    const fields = {
        'installmentCustomerName': customerData.name,
        'installmentCustomerPhone': customerData.phone,
        'installmentCustomerEmail': customerData.email,
        'installmentCustomerAddress': customerData.address
    };

    Object.keys(fields).forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field && fields[fieldId]) {
            field.value = fields[fieldId];
            field.readOnly = true; // Make read-only for existing customers
        }
    });

    // Store customer ID for later use
    const modal = document.getElementById('installmentCustomerModal');
    if (modal) {
        modal.dataset.existingCustomerId = customerData.id;
    }
}

function clearInstallmentCustomerForm() {
    const fieldIds = [
        'installmentCustomerName', 'installmentCustomerPhone', 'installmentCustomerEmail',
        'installmentCustomerNationalId', 'installmentCustomerAddress', 'installmentCustomerRegion',
        'installmentCustomerOccupation', 'installmentEmergencyName', 'installmentEmergencyPhone',
        'installmentEmergencyRelation'
    ];

    fieldIds.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            field.value = '';
            field.readOnly = false;
        }
    });

    // Clear stored customer ID
    const modal = document.getElementById('installmentCustomerModal');
    if (modal) {
        delete modal.dataset.existingCustomerId;
    }
}

function toggleInstallmentCustomerFields(showNewCustomerFields) {
    const newCustomerFieldsContainer = document.getElementById('installmentNewCustomerFields');
    const existingCustomerSelect = document.getElementById('installmentExistingCustomer');
    
    if (showNewCustomerFields) {
        if (newCustomerFieldsContainer) {
            newCustomerFieldsContainer.style.display = 'block';
        }
        if (existingCustomerSelect) {
            existingCustomerSelect.disabled = true;
        }
    } else {
        if (newCustomerFieldsContainer) {
            newCustomerFieldsContainer.style.display = 'none';
        }
        if (existingCustomerSelect) {
            existingCustomerSelect.disabled = false;
        }
    }
}

function showInstallmentCustomerModal() {
    if (cart.length === 0) {
        alert('Please add items to cart before setting up installment payment');
        return;
    }

    const totalAmount = parseFloat(cartTotal.textContent.replace(/,/g, ''));
    const suggestedDownPayment = Math.max(totalAmount * 0.2, 50000); // Minimum 20% or 50,000 TZS

    // Pre-fill form data
    document.getElementById('installmentTotalAmount').textContent = `TZS ${totalAmount.toLocaleString()}`;
    document.getElementById('installmentDownPayment').value = suggestedDownPayment;
    
    // Set minimum down payment
    document.getElementById('installmentDownPayment').setAttribute('min', totalAmount * 0.1); // 10% minimum
    
    // Load existing customers into dropdown
    loadInstallmentCustomers();
    
    // Update summary
    updateInstallmentSummary();

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('installmentCustomerModal'));
    modal.show();
}

function loadInstallmentCustomers() {
    fetch('/api/customers')
        .then(response => response.json())
        .then(data => {
            const customerSelect = document.getElementById('installmentExistingCustomer');
            if (customerSelect) {
                customerSelect.innerHTML = '<option value="">Select existing customer</option>';
                
                if (data.success && data.customers) {
                    data.customers.forEach(customer => {
                        const option = document.createElement('option');
                        option.value = customer.id;
                        option.textContent = `${customer.name} - ${customer.phone || 'No phone'}`;
                        option.dataset.customerData = JSON.stringify(customer);
                        customerSelect.appendChild(option);
                    });
                }
            }
        })
        .catch(error => {
            console.error('Error loading customers:', error);
        });
}

function updateInstallmentSummary() {
    const totalAmount = parseFloat(cartTotal.textContent.replace(/,/g, ''));
    const downPayment = parseFloat(document.getElementById('installmentDownPayment').value) || 0;
    const period = parseInt(document.getElementById('installmentPeriod').value) || 12;
    
    const remainingAmount = totalAmount - downPayment;
    const monthlyPayment = remainingAmount / period;
    
    document.getElementById('installmentDownPaymentDisplay').textContent = `TZS ${downPayment.toLocaleString()}`;
    document.getElementById('installmentRemainingAmount').textContent = `TZS ${remainingAmount.toLocaleString()}`;
    document.getElementById('installmentMonthlyPayment').textContent = `TZS ${monthlyPayment.toLocaleString()}`;
    
    // Validate minimum down payment
    const minDownPayment = totalAmount * 0.1;
    if (downPayment < minDownPayment) {
        document.getElementById('installmentDownPayment').setCustomValidity(`Minimum down payment is TZS ${minDownPayment.toLocaleString()}`);
    } else {
        document.getElementById('installmentDownPayment').setCustomValidity('');
    }
}

function saveInstallmentCustomerInfo() {
    const form = document.getElementById('installmentCustomerForm');
    
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const totalAmount = parseFloat(cartTotal.textContent.replace(/,/g, ''));
    const downPayment = parseFloat(document.getElementById('installmentDownPayment').value);
    const period = parseInt(document.getElementById('installmentPeriod').value);
    
    // Validate down payment
    if (downPayment < totalAmount * 0.1) {
        alert('Down payment must be at least 10% of total amount');
        return;
    }

    const modal = document.getElementById('installmentCustomerModal');
    const existingCustomerId = modal.dataset.existingCustomerId;
    
    // Collect customer data
    installmentCustomerData = {
        customer_id: existingCustomerId || null,
        name: document.getElementById('installmentCustomerName').value,
        phone: document.getElementById('installmentCustomerPhone').value,
        email: document.getElementById('installmentCustomerEmail').value,
        national_id: document.getElementById('installmentCustomerNationalId').value,
        address: document.getElementById('installmentCustomerAddress').value,
        region: document.getElementById('installmentCustomerRegion').value,
        occupation: document.getElementById('installmentCustomerOccupation').value,
        emergency_contact: {
            name: document.getElementById('installmentEmergencyName').value,
            phone: document.getElementById('installmentEmergencyPhone').value,
            relation: document.getElementById('installmentEmergencyRelation').value
        },
        installment_plan: {
            down_payment: downPayment,
            period_months: period,
            monthly_payment: (totalAmount - downPayment) / period
        },
        is_existing_customer: !!existingCustomerId
    };

    // If new customer, create customer first
    if (!existingCustomerId) {
        const customerData = {
            name: installmentCustomerData.name,
            phone: installmentCustomerData.phone,
            email: installmentCustomerData.email,
            address: installmentCustomerData.address,
            customer_type: 'retail'
        };

        fetch('/api/customers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(customerData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                installmentCustomerData.customer_id = data.customer_id;
                finalizeSaveInstallmentCustomer();
            } else {
                alert('Error creating customer: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error creating customer:', error);
            alert('Error creating customer');
        });
    } else {
        finalizeSaveInstallmentCustomer();
    }
}

function finalizeSaveInstallmentCustomer() {
    // Update checkout form with customer data
    const customerNameField = document.getElementById('customerName');
    const customerPhoneField = document.getElementById('customerPhone');
    
    if (customerNameField) customerNameField.value = installmentCustomerData.name;
    if (customerPhoneField) customerPhoneField.value = installmentCustomerData.phone;
    
    // Update payment amount to down payment
    if (paymentAmount) {
        paymentAmount.value = installmentCustomerData.installment_plan.down_payment;
    }

    // Show installment fields in main form
    const installmentFields = document.getElementById('installmentFields');
    if (installmentFields) {
        installmentFields.classList.remove('d-none');
        
        const downPaymentField = document.getElementById('downPayment');
        const numberOfInstallmentsField = document.getElementById('numberOfInstallments');
        const customerAddressField = document.getElementById('customerAddress');
        
        if (downPaymentField) downPaymentField.value = installmentCustomerData.installment_plan.down_payment;
        if (numberOfInstallmentsField) numberOfInstallmentsField.value = installmentCustomerData.installment_plan.period_months;
        if (customerAddressField) customerAddressField.value = installmentCustomerData.address;
    }

    // Close modal
    const modalInstance = bootstrap.Modal.getInstance(document.getElementById('installmentCustomerModal'));
    modalInstance.hide();

    // Show success message
    const customerType = installmentCustomerData.customer_id ? 'existing' : 'new';
    showSuccessAlert(`${customerType.charAt(0).toUpperCase() + customerType.slice(1)} customer information saved! You can now complete the installment sale.`);
}

function showSuccessAlert(message) {
    const alert = document.createElement('div');
    alert.className = 'alert alert-success alert-dismissible fade show position-fixed';
    alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alert.innerHTML = `
        <i class="fas fa-check-circle me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alert);
    
    setTimeout(() => {
        if (alert.parentNode) alert.remove();
    }, 5000);
}

// Completed Transactions Functionality
function initializeCompletedTransactions() {
    // Move existing POS content to the POS tab
    const posContent = document.querySelector('.sales-dashboard .row');
    const posSection = document.getElementById('pos-section');
    if (posContent && posSection && posContent.parentNode.classList.contains('sales-dashboard')) {
        posSection.appendChild(posContent);
    }

    // Event listeners for completed transactions
    const completedTab = document.getElementById('completed-tab');
    const filterBtn = document.getElementById('filterCompletedBtn');
    const clearFiltersBtn = document.getElementById('clearFiltersBtn');

    if (completedTab) {
        completedTab.addEventListener('click', function() {
            loadCompletedTransactions();
        });
    }

    if (filterBtn) {
        filterBtn.addEventListener('click', function() {
            loadCompletedTransactions();
        });
    }

    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', function() {
            document.getElementById('dateFromFilter').value = '';
            document.getElementById('dateToFilter').value = '';
            document.getElementById('paymentMethodFilter').value = '';
            loadCompletedTransactions();
        });
    }
}

function loadCompletedTransactions(page = 1) {
    const dateFrom = document.getElementById('dateFromFilter')?.value || '';
    const dateTo = document.getElementById('dateToFilter')?.value || '';
    const paymentMethod = document.getElementById('paymentMethodFilter')?.value || '';

    // Build query parameters
    const params = new URLSearchParams({
        page: page,
        per_page: 20
    });

    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    if (paymentMethod) params.append('payment_method', paymentMethod);

    // Show loading state
    const tbody = document.getElementById('completedTransactionsBody');
    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4">
                    <i class="fas fa-spinner fa-spin fa-2x text-muted mb-2"></i>
                    <div>Loading completed transactions...</div>
                </td>
            </tr>
        `;
    }

    fetch(`/api/sales/completed?${params.toString()}`, {
        credentials: 'same-origin'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            displayCompletedTransactions(data);
        } else {
            throw new Error(data.error || 'Failed to load transactions');
        }
    })
    .catch(error => {
        console.error('Error loading completed transactions:', error);
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-4 text-danger">
                        <i class="fas fa-exclamation-triangle fa-2x mb-2"></i>
                        <div>Error loading transactions: ${error.message}</div>
                    </td>
                </tr>
            `;
        }
    });
}

function displayCompletedTransactions(data) {
    const tbody = document.getElementById('completedTransactionsBody');
    const pagination = document.getElementById('transactionsPagination');

    // Update summary cards
    updateTransactionsSummary(data.summary);

    if (!data.sales || data.sales.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4 text-muted">
                    <i class="fas fa-info-circle fa-2x mb-2"></i>
                    <div>No completed transactions found</div>
                </td>
            </tr>
        `;
        pagination.classList.add('d-none');
        return;
    }

    // Display transactions
    let html = '';
    data.sales.forEach(sale => {
        const date = new Date(sale.created_at);
        const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
        
        html += `
            <tr>
                <td>
                    <span class="fw-bold text-primary">${sale.sale_number}</span>
                </td>
                <td>
                    <div class="small">${formattedDate}</div>
                </td>
                <td>
                    <div class="fw-bold">${sale.customer_name}</div>
                    ${sale.customer_phone ? `<div class="small text-muted">${sale.customer_phone}</div>` : ''}
                </td>
                <td>
                    <div class="fw-bold">${sale.items_count} item${sale.items_count !== 1 ? 's' : ''}</div>
                    <div class="small text-muted">
                        ${sale.items.slice(0, 2).map(item => `${item.name} (${item.quantity})`).join(', ')}
                        ${sale.items.length > 2 ? `... +${sale.items.length - 2} more` : ''}
                    </div>
                </td>
                <td>
                    <span class="badge bg-primary">${formatPaymentMethod(sale.payment_method)}</span>
                </td>
                <td>
                    <span class="fw-bold text-success">TZS ${sale.total_amount.toLocaleString()}</span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="viewTransactionDetails('${sale.id}')" title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-outline-success" onclick="printTransactionReceipt('${sale.sale_number}')" title="Print Receipt">
                            <i class="fas fa-print"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = html;

    // Update pagination
    if (data.pagination.pages > 1) {
        displayPagination(data.pagination);
        pagination.classList.remove('d-none');
    } else {
        pagination.classList.add('d-none');
    }
}

function updateTransactionsSummary(summary) {
    const totalCount = document.getElementById('totalCompletedCount');
    const totalRevenue = document.getElementById('totalCompletedRevenue');
    const averageTransaction = document.getElementById('averageTransactionValue');
    const todaysCount = document.getElementById('todaysSalesCount');

    if (totalCount) totalCount.textContent = summary.total_completed_sales.toLocaleString();
    if (totalRevenue) totalRevenue.textContent = `TZS ${summary.total_revenue.toLocaleString()}`;
    if (averageTransaction) averageTransaction.textContent = `TZS ${summary.average_transaction.toLocaleString()}`;
    
    // Calculate today's sales from current data (simplified)
    if (todaysCount) {
        const today = new Date().toISOString().split('T')[0];
        // This would need additional API call for accurate today's count
        todaysCount.textContent = '0'; // Placeholder
    }
}

function formatPaymentMethod(method) {
    const methods = {
        'cash': 'Cash',
        'mobile_money': 'Mobile Money',
        'card': 'Card',
        'bank_transfer': 'Bank Transfer',
        'installment': 'Installment'
    };
    return methods[method] || method.charAt(0).toUpperCase() + method.slice(1);
}

function displayPagination(pagination) {
    const paginationContainer = document.querySelector('#transactionsPagination .pagination');
    if (!paginationContainer) return;

    let html = '';

    // Previous button
    if (pagination.has_prev) {
        html += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadCompletedTransactions(${pagination.page - 1}); return false;">
                    <i class="fas fa-chevron-left"></i>
                </a>
            </li>
        `;
    }

    // Page numbers
    const startPage = Math.max(1, pagination.page - 2);
    const endPage = Math.min(pagination.pages, pagination.page + 2);

    if (startPage > 1) {
        html += `<li class="page-item"><a class="page-link" href="#" onclick="loadCompletedTransactions(1); return false;">1</a></li>`;
        if (startPage > 2) {
            html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
    }

    for (let i = startPage; i <= endPage; i++) {
        html += `
            <li class="page-item ${i === pagination.page ? 'active' : ''}">
                <a class="page-link" href="#" onclick="loadCompletedTransactions(${i}); return false;">${i}</a>
            </li>
        `;
    }

    if (endPage < pagination.pages) {
        if (endPage < pagination.pages - 1) {
            html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
        html += `<li class="page-item"><a class="page-link" href="#" onclick="loadCompletedTransactions(${pagination.pages}); return false;">${pagination.pages}</a></li>`;
    }

    // Next button
    if (pagination.has_next) {
        html += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadCompletedTransactions(${pagination.page + 1}); return false;">
                    <i class="fas fa-chevron-right"></i>
                </a>
            </li>
        `;
    }

    paginationContainer.innerHTML = html;
}

function viewTransactionDetails(saleId) {
    // Create and show a modal with transaction details
    const modalHtml = `
        <div class="modal fade" id="transactionDetailsModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Transaction Details</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="text-center">
                            <i class="fas fa-spinner fa-spin fa-2x"></i>
                            <div class="mt-2">Loading transaction details...</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Remove existing modal if any
    const existingModal = document.getElementById('transactionDetailsModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('transactionDetailsModal'));
    modal.show();

    // Load transaction details
    fetch(`/api/sales/${saleId}`, {
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayTransactionDetailsInModal(data.sale);
        } else {
            throw new Error(data.error || 'Failed to load transaction details');
        }
    })
    .catch(error => {
        console.error('Error loading transaction details:', error);
        const modalBody = document.querySelector('#transactionDetailsModal .modal-body');
        modalBody.innerHTML = `
            <div class="text-center text-danger">
                <i class="fas fa-exclamation-triangle fa-2x"></i>
                <div class="mt-2">Error loading transaction details</div>
            </div>
        `;
    });
}

function printTransactionReceipt(saleNumber) {
    // Simple receipt printing functionality
    window.open(`/api/sales/receipt/${saleNumber}`, '_blank');
}

// Make functions global
window.loadCompletedTransactions = loadCompletedTransactions;
window.viewTransactionDetails = viewTransactionDetails;
window.printTransactionReceipt = printTransactionReceipt;
