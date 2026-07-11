"""
M-Pesa Integration Module for Badge Issuance Payments
"""
import os
import json
import base64
import logging
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class MpesaIntegration:
    """M-Pesa STK Push integration for badge payments"""
    
    def __init__(self):
        self.consumer_key = os.environ.get('MPESA_CONSUMER_KEY')
        self.consumer_secret = os.environ.get('MPESA_CONSUMER_SECRET')
        self.passkey = os.environ.get('MPESA_PASSKEY')
        self.shortcode = os.environ.get('MPESA_SHORTCODE', '174379')
        self.callback_url = os.environ.get('MPESA_CALLBACK_URL')
        self.environment = os.environ.get('MPESA_ENVIRONMENT', 'sandbox')
        
        # API endpoints
        if self.environment == 'production':
            self.base_url = 'https://api.safaricom.co.ke'
        else:
            self.base_url = 'https://sandbox.safaricom.co.ke'
    
    def get_access_token(self):
        """Get OAuth access token from M-Pesa"""
        try:
            auth_url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
            auth = base64.b64encode(
                f"{self.consumer_key}:{self.consumer_secret}".encode()
            ).decode()
            
            headers = {'Authorization': f'Basic {auth}'}
            response = requests.get(auth_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('access_token')
            else:
                logger.error(f"Failed to get access token: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            return None
    
    def stk_push(self, phone_number, amount, account_reference, transaction_desc="Badge Issuance"):
        """
        Initiate STK Push payment
        
        Args:
            phone_number: Customer phone number (format: 2547XXXXXXXX)
            amount: Amount to charge
            account_reference: Reference for the transaction
            transaction_desc: Description of the transaction
        
        Returns:
            dict: {'success': bool, 'message': str, 'data': dict}
        """
        try:
            # Format phone number
            phone = self._format_phone(phone_number)
            if not phone:
                return {
                    'success': False,
                    'message': 'Invalid phone number format. Use 2547XXXXXXXX'
                }
            
            # Get access token
            token = self.get_access_token()
            if not token:
                return {
                    'success': False,
                    'message': 'Failed to authenticate with M-Pesa API'
                }
            
            # Generate timestamp and password
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password_str = f"{self.shortcode}{self.passkey}{timestamp}"
            password = base64.b64encode(password_str.encode()).decode()
            
            # Prepare STK Push payload
            payload = {
                'BusinessShortCode': self.shortcode,
                'Password': password,
                'Timestamp': timestamp,
                'TransactionType': 'CustomerPayBillOnline',
                'Amount': str(amount),
                'PartyA': phone,
                'PartyB': self.shortcode,
                'PhoneNumber': phone,
                'CallBackURL': self.callback_url,
                'AccountReference': account_reference,
                'TransactionDesc': transaction_desc
            }
            
            # Send STK Push request
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ResponseCode') == '0':
                    return {
                        'success': True,
                        'message': 'Payment initiated. Please check your phone.',
                        'data': {
                            'checkout_request_id': data.get('CheckoutRequestID'),
                            'merchant_request_id': data.get('MerchantRequestID'),
                            'response_code': data.get('ResponseCode'),
                            'customer_message': data.get('CustomerMessage')
                        }
                    }
                else:
                    return {
                        'success': False,
                        'message': data.get('ResponseDescription', 'Payment initiation failed'),
                        'data': data
                    }
            else:
                logger.error(f"STK Push failed: {response.text}")
                return {
                    'success': False,
                    'message': 'Payment service temporarily unavailable'
                }
                
        except Exception as e:
            logger.error(f"STK Push error: {e}")
            return {
                'success': False,
                'message': f'Error initiating payment: {str(e)}'
            }
    
    def query_status(self, checkout_request_id):
        """
        Query the status of an STK Push transaction
        
        Args:
            checkout_request_id: The CheckoutRequestID from stk_push response
        
        Returns:
            dict: Transaction status
        """
        try:
            token = self.get_access_token()
            if not token:
                return {'success': False, 'message': 'Authentication failed'}
            
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password_str = f"{self.shortcode}{self.passkey}{timestamp}"
            password = base64.b64encode(password_str.encode()).decode()
            
            payload = {
                'BusinessShortCode': self.shortcode,
                'Password': password,
                'Timestamp': timestamp,
                'CheckoutRequestID': checkout_request_id
            }
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'data': data
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to query transaction status'
                }
                
        except Exception as e:
            logger.error(f"Query status error: {e}")
            return {'success': False, 'message': str(e)}
    
    def _format_phone(self, phone_number):
        """Format phone number to M-Pesa format (2547XXXXXXXX)"""
        # Remove any non-digit characters
        phone = ''.join(filter(str.isdigit, str(phone_number)))
        
        # Check if it starts with 0
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        # Check if it starts with 7
        elif phone.startswith('7'):
            phone = '254' + phone
        # Check if it already has 254
        elif phone.startswith('254'):
            pass
        else:
            return None
        
        # Validate length
        if len(phone) != 12:
            return None
        
        return phone

# Singleton instance
mpesa = MpesaIntegration()
