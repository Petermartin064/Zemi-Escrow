# Zemi Africa - Trust-Based Escrow Platform MVP

A backend API for Zemi Africa's escrow checkout platform, built with Django and SQLite.

##  Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL 12+
- M-Pesa Daraja API credentials (sandbox or production)
- Stripe API keys (optional)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/YourUsername/zemi-africa-mvp.git
cd zemi-africa-mvp
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. **Create database**
```bash
createdb zemi_escrow
```

6. **Run migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

7. **Create superuser (optional)**
```bash
python manage.py createsuperuser
```

8. **Run the server**
```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`

---

##  API Documentation

### Base URL
```
http://localhost:8000/api
```

### 1. Create Order (Buyer-Initiated)

**Endpoint:** `POST /api/orders/create`

**Request:**
```json
{
  "buyer_phone": "254712345678",
  "amount": 1500.00,
  "product_description": "iPhone 13 Pro Max 256GB"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "order_reference": "ZEM-A3F8B2",
    "amount": "1500.00",
    "status": "awaiting_payment",
    "delivery_code": "847263",
    "created_at": "2024-12-15T10:30:00Z",
    "message": "Order created successfully. Keep your delivery code safe!"
  }
}
```

**Important:** The delivery code is only returned once during order creation. Store it securely!

---

### 2. Initiate M-Pesa STK Push

**Endpoint:** `POST /api/payments/mpesa/stk-push`

**Request:**
```json
{
  "phone_number": "254712345678",
  "amount": 1500.00,
  "account_reference": "ZEM-A3F8B2",
  "transaction_desc": "Payment for iPhone 13"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "merchant_request_id": "29115-34620561-1",
    "checkout_request_id": "ws_CO_191220191020363925",
    "response_code": "0",
    "response_description": "Success. Request accepted for processing",
    "customer_message": "Success. Request accepted for processing"
  }
}
```

**Flow:**
1. Customer receives M-Pesa PIN prompt on their phone
2. Customer enters PIN to authorize payment
3. M-Pesa processes payment
4. Callback is sent to `/api/webhooks/mpesa`
5. Payment status is updated in system

---

### 3. Payment Webhook (Simulated)

**Endpoint:** `POST /api/webhooks/payment`

**Purpose:** This endpoint simulates a payment provider callback and is SEPARATE from order creation. Only this endpoint can mark orders as paid.

**Request:**
```json
{
  "order_reference": "ZEM-A3F8B2",
  "transaction_id": "QHJ41HG1W8",
  "amount": 1500.00,
  "payment_method": "mpesa",
  "payer_phone": "254712345678",
  "metadata": {
    "mpesa_receipt": "QHJ41HG1W8",
    "transaction_date": "2024-12-15T10:35:00Z"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "order_reference": "ZEM-A3F8B2",
    "transaction_id": "QHJ41HG1W8",
    "status": "paid",
    "paid_at": "2024-12-15T10:35:00Z"
  }
}
```

**Security Notes:**
- This endpoint validates order status transitions
- Only `awaiting_payment` orders can be marked as `paid`
- Transaction IDs must be unique
- Payment amount must match order amount

---

### 4. Confirm Delivery

**Endpoint:** `POST /api/orders/confirm-delivery`

**Request:**
```json
{
  "order_reference": "ZEM-A3F8B2",
  "delivery_code": "847263"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "order_reference": "ZEM-A3F8B2",
    "status": "completed",
    "completed_at": "2024-12-15T14:30:00Z",
    "payout_initiated": true,
    "message": "Delivery confirmed. Payment is being released to seller."
  }
}
```

**Security:**
- Delivery codes are hashed in the database
- Invalid codes are rejected
- Only `paid` orders can be completed

---

### 5. Get Order Details

**Endpoint:** `GET /api/orders/{order_reference}`

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "order_reference": "ZEM-A3F8B2",
    "buyer_phone_masked": "****5678",
    "amount": "1500.00",
    "product_description": "iPhone 13 Pro Max 256GB",
    "status": "completed",
    "created_at": "2024-12-15T10:30:00Z",
    "paid_at": "2024-12-15T10:35:00Z",
    "completed_at": "2024-12-15T14:30:00Z"
  }
}
```

---

### 6. B2C Payout (Seller Settlement)

**Endpoint:** `POST /api/payments/mpesa/b2c-payout`

**Request:**
```json
{
  "phone_number": "254712345678",
  "amount": 1500.00,
  "order_reference": "ZEM-A3F8B2"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "conversation_id": "AG_20231215_00004e8d0b0e7b6f",
    "originator_conversation_id": "12345-67890-1",
    "response_code": "0",
    "response_description": "Accept the service request successfully."
  }
}
```

---

##  Architecture & Design Decisions

### Database Schema

#### Orders Table
- `id`: UUID primary key
- `order_reference`: Unique order identifier (e.g., ZEM-A3F8B2)
- `buyer_phone_hash`: Hashed phone number (security)
- `buyer_phone_last4`: Last 4 digits for display
- `amount`: Decimal(10, 2)
- `product_description`: Text
- `delivery_code_hash`: Hashed 6-digit code
- `status`: Enum (awaiting_payment, paid, completed, cancelled, refunded)
- Timestamps: created_at, updated_at, paid_at, completed_at

#### Payments Table
- `id`: UUID primary key
- `order_id`: Foreign key to Orders
- `payment_method`: Enum (mpesa, stripe, visa)
- `amount`: Decimal(10, 2)
- `transaction_id`: Unique transaction identifier
- `provider_reference`: External reference from payment provider
- `payer_phone_hash`: Hashed phone number
- `status`: Enum (pending, completed, failed, refunded)
- `metadata`: JSONB for flexible data storage

#### Payouts Table
- `id`: UUID primary key
- `order_id`: Foreign key to Orders
- `payment_id`: Foreign key to Payments
- `amount`: Decimal(10, 2)
- `seller_phone_hash`: Hashed phone number
- `transaction_id`: Payout transaction ID
- `status`: Enum (pending, processing, completed, failed)
- `failure_reason`: Text (nullable)

#### WebhookLogs Table
- `id`: UUID primary key
- `webhook_type`: String (mpesa_stk, stripe, etc.)
- `payload`: JSONB (full webhook payload)
- `headers`: JSONB (request headers)
- `processed`: Boolean
- `processing_error`: Text (nullable)

### Security Implementations

1. **Phone Number Hashing**
   - All phone numbers are hashed using Django's password hasher
   - Only last 4 digits stored in plaintext for display
   - Prevents exposure of PII in case of database breach

2. **Delivery Code Protection**
   - 6-digit codes are hashed before storage
   - Verification uses constant-time comparison
   - Codes are only shown once at order creation

3. **State Machine Validation**
   - Strict order status transitions enforced
   - `awaiting_payment` → `paid` → `completed`
   - Invalid transitions are rejected

4. **Separation of Concerns**
   - Order creation endpoint CANNOT mark orders as paid
   - Only webhook endpoint can update payment status
   - Prevents unauthorized status manipulation

### Key Design Patterns

1. **Service Layer Pattern**
   - `MpesaService` handles all M-Pesa API interactions
   - `StripeService` handles Stripe operations
   - Clean separation from views

2. **Database Transactions**
   - All critical operations use `transaction.atomic()`
   - Ensures data consistency
   - Automatic rollback on errors

3. **Comprehensive Logging**
   - All webhook requests logged to database
   - Structured logging for debugging
   - Audit trail for compliance

---

##  M-Pesa Integration Details

### How Real M-Pesa STK Push Works

1. **Authentication**
   - Get OAuth token using Consumer Key and Secret
   - Token valid for ~3600 seconds
   - Included in all subsequent requests

2. **STK Push Request**
   ```python
   # Generate password
   timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
   password = base64.b64encode(f"{shortcode}{passkey}{timestamp}")
   
   # Make request
   POST https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest
   {
     "BusinessShortCode": "174379",
     "Password": "MTc0Mzc5YmZiMjc5...",
     "Timestamp": "20231215103000",
     "TransactionType": "CustomerPayBillOnline",
     "Amount": 1500,
     "PartyA": "254712345678",
     "PartyB": "174379",
     "PhoneNumber": "254712345678",
     "CallBackURL": "https://yourdomain.com/api/webhooks/mpesa",
     "AccountReference": "ZEM-A3F8B2",
     "TransactionDesc": "Payment"
   }
   ```

3. **Customer Experience**
   - Customer receives STK Push on their phone
   - Enters M-Pesa PIN
   - Confirms payment
   - Receives SMS confirmation

4. **Callback Processing**
   - M-Pesa sends POST request to CallBackURL
   - Payload contains result code and transaction details
   - Application updates payment status
   - Order status transitions to `paid`

### B2C Payment Flow

1. **Seller Payout Request**
   ```python
   POST https://sandbox.safaricom.co.ke/mpesa/b2c/v1/paymentrequest
   {
     "InitiatorName": "testapi",
     "SecurityCredential": "encrypted_credential",
     "CommandID": "BusinessPayment",
     "Amount": 1500,
     "PartyA": "600000",
     "PartyB": "254712345678",
     "Remarks": "Payout for ZEM-A3F8B2",
     "QueueTimeOutURL": "https://yourdomain.com/timeout",
     "ResultURL": "https://yourdomain.com/result",
     "Occasion": "Payout"
   }
   ```

2. **Result Processing**
   - Async callback to ResultURL
   - Contains transaction status
   - Update payout record in database

---

##  Handling Failed Payments & Timeouts

### 1. STK Push Timeout
**Scenario:** Customer doesn't enter PIN within timeout period (typically 60 seconds)

**Implementation:**
```python
# In mpesa_callback view
if result_code == 1032:  # Request cancelled by user
    # Mark payment as failed
    payment.status = 'failed'
    payment.metadata['failure_reason'] = 'User cancelled'
    payment.save()
    
    # Send notification to buyer
    send_notification(
        phone=order.buyer_phone,
        message="Payment cancelled. Try again when ready."
    )
```

**Recommended Actions:**
- Log timeout events for analytics
- Allow customer to retry payment
- Send SMS reminder with payment link
- Set order expiry time (e.g., 24 hours)

### 2. Insufficient Balance
**Scenario:** Customer has insufficient M-Pesa balance

**Implementation:**
```python
if result_code == 1:  # Insufficient balance
    payment.status = 'failed'
    payment.metadata['failure_reason'] = 'Insufficient balance'
    payment.save()
    
    # Notify customer
    send_notification(
        phone=order.buyer_phone,
        message="Payment failed. Please top up and try again."
    )
```

### 3. Network Failures
**Scenario:** M-Pesa API unreachable or timeout

**Implementation:**
```python
# In MpesaService.stk_push()
try:
    response = requests.post(url, json=payload, timeout=30)
except requests.Timeout:
    # Implement retry with exponential backoff
    for attempt in range(3):
        time.sleep(2 ** attempt)
        try:
            response = requests.post(url, json=payload, timeout=30)
            break
        except requests.Timeout:
            if attempt == 2:
                # Final failure
                return {
                    'success': False,
                    'error': 'Service temporarily unavailable'
                }
```

**Recommended Strategy:**
- Queue failed payments for retry (use Celery)
- Implement circuit breaker pattern
- Monitor payment success rates
- Alert team if failure rate exceeds threshold

### 4. Duplicate Transactions
**Scenario:** Customer clicks payment button multiple times

**Implementation:**
```python
# Check for existing pending payment
existing_payment = Payment.objects.filter(
    order=order,
    status='pending',
    created_at__gte=timezone.now() - timedelta(minutes=5)
).first()

if existing_payment:
    return Response({
        'success': False,
        'error': 'Payment already in progress'
    })
```

### 5. Payment Reconciliation
**Daily Job Implementation:**
```python
# management/commands/reconcile_payments.py
from django.core.management.base import BaseCommand
from datetime import timedelta
from django.utils import timezone

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Find pending payments older than 1 hour
        stale_payments = Payment.objects.filter(
            status='pending',
            created_at__lt=timezone.now() - timedelta(hours=1)
        )
        
        for payment in stale_payments:
            # Query M-Pesa for transaction status
            mpesa = MpesaService()
            result = mpesa.query_transaction_status(
                payment.metadata['checkout_request_id']
            )
            
            # Update payment based on actual status
            if result['ResultCode'] == '0':
                payment.status = 'completed'
            else:
                payment.status = 'failed'
            payment.save()
```

---

##  Fraud Prevention & Abuse Reduction

### 1. Rate Limiting
```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10/minute',  # Anonymous users
        'user': '100/minute',  # Authenticated users
        'order_creation': '5/hour',  # Per phone number
    }
}
```

### 2. Phone Number Verification
```python
# Implement OTP verification before order creation
def verify_phone_otp(phone_number, otp_code):
    """Verify phone number using OTP via Africa's Talking"""
    # Send OTP
    # Verify before allowing order creation
    pass
```

### 3. Velocity Checks
```python
# Prevent rapid order creation from same phone
recent_orders = Order.objects.filter(
    buyer_phone_hash=phone_hash,
    created_at__gte=timezone.now() - timedelta(hours=1)
).count()

if recent_orders >= 5:
    raise ValidationError("Too many orders. Please wait.")
```

### 4. Amount Limits
```python
# In serializers.py
def validate_amount(self, value):
    # Daily limit per phone number
    today_total = Order.objects.filter(
        buyer_phone_hash=get_phone_hash(phone),
        created_at__date=timezone.now().date()
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    if today_total + value > 50000:  # 50k KES daily limit
        raise ValidationError("Daily transaction limit exceeded")
    
    return value
```

### 5. Delivery Code Protection
```python
# Implement attempt limiting
class DeliveryAttempt(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    attempted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()

# In confirm_delivery view
recent_attempts = DeliveryAttempt.objects.filter(
    order=order,
    attempted_at__gte=timezone.now() - timedelta(minutes=15)
).count()

if recent_attempts >= 3:
    # Lock order for 1 hour
    order.locked_until = timezone.now() + timedelta(hours=1)
    order.save()
    raise ValidationError("Too many attempts. Order locked.")
```

### 6. Seller Verification
```python
class Seller(models.Model):
    phone_number_hash = models.CharField(max_length=255, unique=True)
    verification_status = models.CharField(
        choices=[('unverified', 'pending', 'verified', 'suspended')]
    )
    trust_score = models.IntegerField(default=0)
    successful_transactions = models.IntegerField(default=0)
    
    # KYC documents
    id_number_hash = models.CharField(max_length=255)
    id_document_url = models.URLField()
    verified_at = models.DateTimeField(null=True)
```

### 7. Dispute Resolution System
```python
class Dispute(models.Model):
    DISPUTE_TYPES = [
        ('non_delivery', 'Non Delivery'),
        ('wrong_item', 'Wrong Item'),
        ('damaged', 'Damaged Product'),
        ('fraud', 'Fraud')
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    dispute_type = models.CharField(choices=DISPUTE_TYPES)
    description = models.TextField()
    evidence_urls = models.JSONField(default=list)
    status = models.CharField(
        choices=[('open', 'investigating', 'resolved', 'closed')]
    )
    resolution = models.TextField(null=True)
```

---

## Product Improvement Proposal

### Feature: **Smart Escrow Release with Multi-Party Verification**

#### What to Improve
Implement a flexible multi-party verification system that goes beyond simple delivery code confirmation.

#### Current Flow Problem
- Single delivery code can be shared/stolen
- No dispute mechanism before fund release
- Buyer has full control over fund release
- No way to handle partial deliveries or quality issues

#### Proposed Solution

**1. Multi-Stage Verification**
```python
class OrderVerification(models.Model):
    order = models.ForeignKey(Order)
    verification_type = models.CharField(
        choices=[
            ('delivery_code', 'Delivery Code'),
            ('photo_proof', 'Photo Proof'),
            ('geolocation', 'Geolocation'),
            ('third_party', 'Third Party Inspector')
        ]
    )
    status = models.CharField(choices=[('pending', 'verified', 'failed')])
    confidence_score = models.FloatField()  # 0-100
```

**2. Gradual Release**
```python
# Release funds in stages
class PayoutSchedule(models.Model):
    order = models.ForeignKey(Order)
    milestone = models.CharField()  # "shipped", "delivered", "inspected"
    percentage = models.FloatField()  # e.g., 30%, 70%, 100%
    status = models.CharField()
    released_at = models.DateTimeField(null=True)

# Example:
# 30% on delivery confirmation
# 70% after 48-hour inspection period
# 100% if no disputes raised
```

**3. AI-Powered Fraud Detection**
```python
def calculate_risk_score(order):
    """Machine learning model to assess transaction risk"""
    factors = {
        'new_buyer': 0.3,
        'new_seller': 0.3,
        'high_value': 0.2 if order.amount > 10000 else 0,
        'velocity': check_velocity_pattern(order),
        'location_match': check_buyer_seller_proximity(order)
    }
    return sum(factors.values())

# High-risk orders require additional verification
if risk_score > 0.7:
    order.requires_manual_review = True
```

**4. Photo Verification**
```python
# Buyer uploads photo of received product
class DeliveryProof(models.Model):
    order = models.ForeignKey(Order)
    photo_url = models.URLField()
    timestamp = models.DateTimeField()
    gps_coordinates = models.CharField()
    verified = models.BooleanField(default=False)
```

**5. Reputation System**
```python
class UserReputation(models.Model):
    user_phone_hash = models.CharField(unique=True)
    trust_score = models.FloatField(default=50.0)  # 0-100
    total_transactions = models.IntegerField()
    successful_rate = models.FloatField()
    average_response_time = models.DurationField()
    dispute_count = models.IntegerField()
    
    def update_score(self, transaction_outcome):
        """Update trust score based on transaction"""
        if transaction_outcome == 'success':
            self.trust_score = min(100, self.trust_score + 0.5)
        elif transaction_outcome == 'dispute':
            self.trust_score = max(0, self.trust_score - 5)
```

#### Why It Matters

**For Buyers:**
- Increased confidence in transactions
- Protection against fake delivery confirmations
- Option to inspect before full payment release
- Clear dispute resolution process

**For Sellers:**
- Faster payment for trusted sellers (higher trust score)
- Protection against false fraud claims
- Incentive to maintain quality service
- Clear path to build reputation

**For Zemi:**
- Reduced fraud losses
- Lower dispute resolution costs
- Better data for risk assessment
- Competitive advantage in market
- Ability to offer insurance products based on risk scores

**For the Market:**
- Increases trust in social commerce
- Enables higher-value transactions
- Reduces need for cash-on-delivery
- Formalizes informal trade

#### Implementation Priority
1. **Phase 1 (Weeks 1-2):** Photo verification + GPS
2. **Phase 2 (Weeks 3-4):** Gradual release system
3. **Phase 3 (Month 2):** Reputation system
4. **Phase 4 (Month 3):** AI fraud detection

#### Success Metrics
- Fraud rate reduction: Target <0.1%
- Dispute resolution time: <24 hours
- User trust score: Increase to 4.5+/5
- Transaction volume: 50% increase
- Average transaction value: 30% increase

---

##  Project Structure

```
zemi-africa-mvp/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── zemi_escrow/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── api/
    ├── __init__.py
    ├── models.py
    ├── serializers.py
    ├── views.py
    ├── urls.py
    ├── admin.py
    ├── services/
    │   ├── __init__.py
    │   ├── mpesa_service.py
    │   └── stripe_service.py
    ├── management/
    │   └── commands/
    │       └── reconcile_payments.py
    └── tests/
        ├── __init__.py
        ├── test_orders.py
        ├── test_payments.py
        └── test_webhooks.py
```

---

## 🧪 Testing

### Run Tests
```bash
python manage.py test api.tests
```

### Test Coverage
```bash
pip install coverage
coverage run --source='.' manage.py test api
coverage report
```

### Manual Testing with cURL

**Create Order:**
```bash
curl -X POST http://localhost:8000/api/orders/create \
  -H "Content-Type: application/json" \
  -d '{
    "buyer_phone": "254712345678",
    "amount": 1500.00,
    "product_description": "iPhone 13"
  }'
```

**Simulate Payment:**
```bash
curl -X POST http://localhost:8000/api/webhooks/payment \
  -H "Content-Type: application/json" \
  -d '{
    "order_reference": "ZEM-A3F8B2",
    "transaction_id": "QHJ41HG1W8",
    "amount": 1500.00,
    "payment_method": "mpesa"
  }'
```

---

### Environment Variables
```bash
DJANGO_SECRET_KEY=your-secret-key
DEBUG=False
DB_NAME=zemi_escrow
DB_USER=postgres
DB_PASSWORD=secure-password
DB_HOST=localhost
DB_PORT=5432

MPESA_ENVIRONMENT=production
MPESA_CONSUMER_KEY=your-key
MPESA_CONSUMER_SECRET=your-secret
MPESA_SHORTCODE=your-shortcode
MPESA_PASSKEY=your-passkey
MPESA_CALLBACK_URL=https://yourdomain.com/api/webhooks/mpesa/

```

---

## 📝 Assumptions Made

1. **Phone Numbers:** All phone numbers are Kenyan (+254 format)
2. **Currency:** All amounts are in Kenyan Shillings (KES)
3. **Payment Flow:** Single payment per order (no partial payments)
4. **Seller Info:** Seller phone = Buyer phone (for MVP simulation)
5. **Delivery:** Physical delivery with in-person confirmation
6. **Timeout:** Orders expire after 24 hours if not paid
7. **Refunds:** Manual refund process (not automated yet)
8. **Authentication:** No user authentication (phone-based identification)
9. **Business Model:** Zemi takes a commission (not implemented in MVP)
10. **Support:** Customer support handled externally (no built-in system)

---

## 👤 Author

** Peter Martin**
- GitHub: [@Petermartin064](https://github.com/Petermartin064)
- Email: petermartin602@gmail.com

---

## Acknowledgments

- Zemi Africa team for the challenge
- Safaricom Daraja API documentation
- Django REST Framework community
- All open-source contributors

---

**Built with ❤️ for Zemi Africa Engineering Challenge**
