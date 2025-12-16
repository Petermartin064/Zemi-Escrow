import requests
import base64
from datetime import datetime
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class MpesaService:
    """Service class for M-Pesa Daraja API integration"""
    
    def __init__(self):
        self.environment = settings.MPESA_ENVIRONMENT
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.shortcode = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        self.initiator_name = settings.MPESA_INITIATOR_NAME
        self.security_credential = settings.MPESA_SECURITY_CREDENTIAL
        self.base_url = 'https://sandbox.safaricom.co.ke'
    
    def get_access_token(self):
        """Get OAuth access token from M-Pesa API"""
        try:
            url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
            
            # Create basic auth header
            auth_string = f"{self.consumer_key}:{self.consumer_secret}"
            auth_bytes = auth_string.encode('ascii')
            auth_base64 = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Basic {auth_base64}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            return result.get('access_token')
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get M-Pesa access token: {str(e)}")
            raise Exception(f"Failed to authenticate with M-Pesa: {str(e)}")
    
    def stk_push(self, phone_number: str, amount: float, account_reference: str, 
                 transaction_desc: str = "Payment"):
        """
        Initiate STK Push (Lipa Na M-Pesa Online)
        
        Args:
            phone_number: Customer phone number (254XXXXXXXXX format)
            amount: Amount to be paid
            account_reference: Account reference (e.g., order reference)
            transaction_desc: Transaction description
        
        Returns:
            dict: Response from M-Pesa API
        """
        try:
            access_token = self.get_access_token()
            
            url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
            
            # Generate timestamp
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            # Generate password
            password_string = f"{self.shortcode}{self.passkey}{timestamp}"
            password_bytes = password_string.encode('ascii')
            password_base64 = base64.b64encode(password_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "BusinessShortCode": self.shortcode,
                "Password": password_base64,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(amount),
                "PartyA": phone_number,
                "PartyB": self.shortcode,
                "PhoneNumber": phone_number,
                "CallBackURL": settings.MPESA_CALLBACK_URL,
                "AccountReference": account_reference,
                "TransactionDesc": transaction_desc
            }
            
            logger.info(f"Initiating STK Push for {phone_number}, Amount: {amount}")
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"STK Push initiated successfully: {result}")
            
            return {
                'success': True,
                'merchant_request_id': result.get('MerchantRequestID'),
                'checkout_request_id': result.get('CheckoutRequestID'),
                'response_code': result.get('ResponseCode'),
                'response_description': result.get('ResponseDescription'),
                'customer_message': result.get('CustomerMessage')
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"STK Push failed: {str(e)}")
            error_message = str(e)
            
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_message = error_data.get('errorMessage', str(e))
                except:
                    pass
            
            return {
                'success': False,
                'error': error_message
            }
        
    
    def query_transaction_status(self, checkout_request_id: str):
        """
        Query the status of an STK Push transaction
        
        Args:
            checkout_request_id: CheckoutRequestID from STK Push response
        
        Returns:
            dict: Transaction status
        """
        try:
            access_token = self.get_access_token()
            
            url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
            
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password_string = f"{self.shortcode}{self.passkey}{timestamp}"
            password_bytes = password_string.encode('ascii')
            password_base64 = base64.b64encode(password_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "BusinessShortCode": self.shortcode,
                "Password": password_base64,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id
            }
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Transaction query failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }