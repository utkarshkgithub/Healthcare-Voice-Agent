"""
Payments API routes — /payments
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
import os
import logging
import hashlib
import hmac
import json

# Try to import razorpay, but don't fail if not installed
try:
    import razorpay
    RAZORPAY_AVAILABLE = True
except ImportError:
    RAZORPAY_AVAILABLE = False
    razorpay = None

router = APIRouter(tags=["payments"])
logger = logging.getLogger(__name__)

# Initialize Razorpay client if keys are available
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")

if RAZORPAY_AVAILABLE and RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    client = None
    logger.warning("Razorpay client not initialized. Missing API keys or package not installed.")


class CreateOrderRequest(BaseModel):
    amount: int  # Amount in paise (e.g., 10000 = ₹100)
    currency: str = "INR"
    receipt: str = None
    notes: dict = None


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.post("/payments/create-order")
def create_order(req: CreateOrderRequest):
    """Create a Razorpay order for payment"""
    if not client:
        raise HTTPException(status_code=503, detail="Payment service unavailable")
    
    try:
        # Create order data
        order_data = {
            "amount": req.amount,
            "currency": req.currency,
            "payment_capture": 1  # Auto capture payment
        }
        
        if req.receipt:
            order_data["receipt"] = req.receipt
        
        if req.notes:
            order_data["notes"] = req.notes
        
        # Create order
        order = client.order.create(data=order_data)
        
        return {
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key_id": RAZORPAY_KEY_ID
        }
    except Exception as e:
        logger.error(f"[payments] Order creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Payment order creation failed: {str(e)}")


@router.post("/payments/verify")
def verify_payment(req: VerifyPaymentRequest):
    """Verify a Razorpay payment signature"""
    if not client:
        raise HTTPException(status_code=503, detail="Payment service unavailable")
    
    try:
        # Verify signature
        params_dict = {
            'razorpay_order_id': req.razorpay_order_id,
            'razorpay_payment_id': req.razorpay_payment_id,
            'razorpay_signature': req.razorpay_signature
        }
        
        # client.utility.verify_payment_signature(params_dict) will raise exception if invalid
        client.utility.verify_payment_signature(params_dict)
        
        # Payment is verified, you can now create appointment or update payment status
        return {
            "verified": True,
            "message": "Payment verified successfully",
            "order_id": req.razorpay_order_id,
            "payment_id": req.razorpay_payment_id
        }
    except razorpay.errors.SignatureVerificationError:
        logger.error(f"[payments] Signature verification failed for order: {req.razorpay_order_id}")
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    except Exception as e:
        logger.error(f"[payments] Verification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Payment verification failed: {str(e)}")


@router.post("/payments/webhook")
async def webhook_handler(
    payload: dict,
    x_razorpay_signature: str = Header(None)
):
    """Handle Razorpay webhook events"""
    if not RAZORPAY_WEBHOOK_SECRET:
        raise HTTPException(status_code=501, detail="Webhook secret not configured")
    
    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing signature header")
    
    try:
        # Verify webhook signature
        body = json.dumps(payload, separators=(',', ':')).encode()
        
        expected_signature = hmac.new(
            RAZORPAY_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(expected_signature, x_razorpay_signature):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
        
        # Handle webhook event
        event = payload.get("event", "")
        payload_data = payload.get("payload", {}).get("payment", {}) or payload.get("payload", {}).get("entity", {})
        
        logger.info(f"[payments] Webhook received: {event} for {payload_data.get('id', 'unknown')}")
        
        # Handle different events
        if event == "payment.captured":
            # Payment successfully captured
            payment_id = payload_data.get("id")
            order_id = payload_data.get("order_id")
            amount = payload_data.get("amount")
            
            logger.info(f"[payments] Payment captured: {payment_id} for order {order_id} amount {amount}")
            
            # Here you would update your database with payment success
            # e.g., mark appointment as paid, update payment status, etc.
            
        elif event == "payment.failed":
            # Payment failed
            payment_id = payload_data.get("id")
            error = payload_data.get("error", {})
            
            logger.error(f"[payments] Payment failed: {payment_id} - {error}")
            
            # Update database with payment failure
        
        return {"status": "ok", "event": event}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[payments] Webhook processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")
