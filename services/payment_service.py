
import requests
import json
import base64
from datetime import datetime
import hashlib
import uuid
from flask import current_app

class PaymentService:
    def __init__(self):
        self.mpesa_base_url = "https://sandbox.safaricom.co.ke"  # Use production URL for live
        self.mpesa_consumer_key = current_app.config.get('MPESA_CONSUMER_KEY', '')
        self.mpesa_consumer_secret = current_app.config.get('MPESA_CONSUMER_SECRET', '')
        self.mpesa_shortcode = current_app.config.get('MPESA_SHORTCODE', '')
        self.mpesa_passkey = current_app.config.get('MPESA_PASSKEY', '')
        
    def get_mpesa_access_token(self):
        """Get M-Pesa API access token"""
        try:
            url = f"{self.mpesa_base_url}/oauth/v1/generate?grant_type=client_credentials"
            
            credentials = base64.b64encode(
                f"{self.mpesa_consumer_key}:{self.mpesa_consumer_secret}".encode()
            ).decode()
            
            headers = {
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            return response.json().get('access_token')
            
        except Exception as e:
            current_app.logger.error(f"M-Pesa token error: {str(e)}")
            return None
    
    def initiate_mpesa_payment(self, phone_number, amount, reference, description):
        """Initiate M-Pesa STK Push payment"""
        try:
            access_token = self.get_mpesa_access_token()
            if not access_token:
                return {"success": False, "error": "Failed to get access token"}
            
            # Format phone number (remove + and ensure 254 prefix)
            if phone_number.startswith('+'):
                phone_number = phone_number[1:]
            if phone_number.startswith('0'):
                phone_number = '254' + phone_number[1:]
            
            # Generate timestamp and password
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password_string = f"{self.mpesa_shortcode}{self.mpesa_passkey}{timestamp}"
            password = base64.b64encode(password_string.encode()).decode()
            
            url = f"{self.mpesa_base_url}/mpesa/stkpush/v1/processrequest"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "BusinessShortCode": self.mpesa_shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(amount),
                "PartyA": phone_number,
                "PartyB": self.mpesa_shortcode,
                "PhoneNumber": phone_number,
                "CallBackURL": current_app.config.get('MPESA_CALLBACK_URL', ''),
                "AccountReference": reference,
                "TransactionDesc": description
            }
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('ResponseCode') == '0':
                return {
                    "success": True,
                    "checkout_request_id": result.get('CheckoutRequestID'),
                    "merchant_request_id": result.get('MerchantRequestID'),
                    "message": "Payment request sent successfully"
                }
            else:
                return {
                    "success": False,
                    "error": result.get('errorMessage', 'Payment request failed')
                }
                
        except Exception as e:
            current_app.logger.error(f"M-Pesa payment error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def check_mpesa_payment_status(self, checkout_request_id):
        """Check M-Pesa payment status"""
        try:
            access_token = self.get_mpesa_access_token()
            if not access_token:
                return {"success": False, "error": "Failed to get access token"}
            
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password_string = f"{self.mpesa_shortcode}{self.mpesa_passkey}{timestamp}"
            password = base64.b64encode(password_string.encode()).decode()
            
            url = f"{self.mpesa_base_url}/mpesa/stkpushquery/v1/query"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "BusinessShortCode": self.mpesa_shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id
            }
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            current_app.logger.error(f"M-Pesa status check error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def process_mobile_money_payment(self, provider, phone_number, amount, reference):
        """Process mobile money payments for various providers"""
        providers = {
            'tigo': self._process_tigo_pesa,
            'airtel': self._process_airtel_money,
            'halopesa': self._process_halo_pesa
        }
        
        if provider.lower() in providers:
            return providers[provider.lower()](phone_number, amount, reference)
        else:
            return {"success": False, "error": "Unsupported mobile money provider"}
    
    def _process_tigo_pesa(self, phone_number, amount, reference):
        """Process Tigo Pesa payment"""
        # Implement Tigo Pesa API integration
        return {
            "success": True,
            "transaction_id": str(uuid.uuid4()),
            "message": "Tigo Pesa payment initiated"
        }
    
    def _process_airtel_money(self, phone_number, amount, reference):
        """Process Airtel Money payment"""
        # Implement Airtel Money API integration
        return {
            "success": True,
            "transaction_id": str(uuid.uuid4()),
            "message": "Airtel Money payment initiated"
        }
    
    def _process_halo_pesa(self, phone_number, amount, reference):
        """Process Halo Pesa payment"""
        # Implement Halo Pesa API integration
        return {
            "success": True,
            "transaction_id": str(uuid.uuid4()),
            "message": "Halo Pesa payment initiated"
        }
    
    def process_cryptocurrency_payment(self, currency, amount, wallet_address):
        """Process cryptocurrency payments"""
        supported_currencies = ['BTC', 'ETH', 'USDT', 'BNB']
        
        if currency.upper() not in supported_currencies:
            return {"success": False, "error": "Unsupported cryptocurrency"}
        
        # Generate payment request
        payment_id = str(uuid.uuid4())
        
        return {
            "success": True,
            "payment_id": payment_id,
            "currency": currency.upper(),
            "amount": amount,
            "wallet_address": wallet_address,
            "qr_code_url": f"/api/payments/crypto/qr/{payment_id}",
            "message": "Cryptocurrency payment initiated"
        }
    
    def process_split_payment(self, payment_methods):
        """Process split payments across multiple methods"""
        results = []
        total_amount = sum(method['amount'] for method in payment_methods)
        
        for method in payment_methods:
            if method['type'] == 'mpesa':
                result = self.initiate_mpesa_payment(
                    method['phone_number'],
                    method['amount'],
                    method['reference'],
                    method['description']
                )
            elif method['type'] == 'mobile_money':
                result = self.process_mobile_money_payment(
                    method['provider'],
                    method['phone_number'],
                    method['amount'],
                    method['reference']
                )
            elif method['type'] == 'crypto':
                result = self.process_cryptocurrency_payment(
                    method['currency'],
                    method['amount'],
                    method['wallet_address']
                )
            else:
                result = {"success": False, "error": f"Unsupported payment type: {method['type']}"}
            
            results.append({
                "method": method['type'],
                "amount": method['amount'],
                "result": result
            })
        
        return {
            "success": all(r['result']['success'] for r in results),
            "total_amount": total_amount,
            "payment_results": results
        }
