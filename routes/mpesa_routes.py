from flask import Blueprint, request, jsonify
from extensions import db
from models import MpesaIntegration, MpesaTransactions, cipher_suite
from services.mpesa_service import get_access_token, register_mpesa_urls

mpesa_bp = Blueprint("mpesa", __name__)

@mpesa_bp.route("/save-integration-settings", methods=["POST"])
def save_integrations():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error':'No JSON data received'}), 400
    except Exception as e:
        return jsonify({'error':f'Invalid JSON format: {str(e)}'}), 400

    user_id = data.get("user_id")
    integrations = data.get("integrations",{})

    if not user_id:
        return jsonify({"message": "User ID is required"}), 400

    resend_data = integrations.get("resend", {})
    mpesa_settings = integrations.get("mpesa", {})

    mpesa_consumer_key = mpesa_settings.get('consumer_key')
    mpesa_consumer_secret = mpesa_settings.get('consumer_secret')
    mpesa_shortcode = mpesa_settings.get('shortcode')
    mpesa_passkey = mpesa_settings.get('passkey')
    mpesa_enabled = mpesa_settings.get('enabled',False)

    if not all([mpesa_consumer_key, mpesa_consumer_secret, mpesa_shortcode, mpesa_passkey]):
            return jsonify({'message': 'Missing M-Pesa credentials', 'status': 'error'}), 400

    access_token = get_access_token(mpesa_consumer_key, mpesa_consumer_secret)

    if access_token:
        validation_url ="https://mydomain.com/validation"
        confirmation_url = "https://mydomain.com/confirmation"

        register_result = register_mpesa_urls(access_token, mpesa_shortcode, validation_url, confirmation_url)

        if register_result and register_result.get('ResponseCode') == '0':
            existing_integration = MpesaIntegration.query.filter_by(user_id=user_id).first()
            if existing_integration:
                existing_integration.shortcode = mpesa_shortcode
                existing_integration.encrypted_consumer_key = cipher_suite.encrypt(mpesa_consumer_key.encode())
                existing_integration.encrypted_consumer_secret = cipher_suite.encrypt(mpesa_consumer_secret.encode())
                existing_integration.encrypted_passkey = cipher_suite.encrypt(mpesa_passkey.encode())
                existing_integration.is_registered = True
                existing_integration.registration_response = register_result
            # Store credentials and registration status in your database
            else:
                integration = MpesaIntegration(
                    user_id=user_id,
                    shortcode=mpesa_shortcode,
                    consumer_key = mpesa_consumer_key,
                    consumer_secret = mpesa_consumer_secret,
                    passkey = mpesa_passkey
                )
                integration.is_registered = True
                integration.registration_response = register_result
                db.session.add(integration)
                db.session.commit()
            return jsonify({'message': 'M-Pesa integration successful', 'status': 'success'}), 200
        else:
            return jsonify({'message': 'Failed to register M-Pesa URLs', 'status': 'error'}), 500
    else:
            return jsonify({'message': 'Failed to get M-Pesa access token', 'status': 'error'}), 500

    return jsonify({
        'message':'Integration setting received',
        'status': 'success'
    }), 200

@mpesa_bp.route("/transactions", methods=["GET"])
def get_transactions():
    user_id = 1
    try:
        transactions = MpesaTransactions.query.filter_by(user_id=user_id).order_by(MpesaTransactions.transaction_time.desc()).all()
        transactions_list = []
        for transaction in transactions:
            transactions_list.append({
                'id':transaction.id,
                'trans_id':transaction.mpesa_trans_id,
                'amount':float(transaction.amount),
                'time':transaction.transaction_time,
                'account_ref':transaction.account_reference,
                'phone_number':transaction.phone_number
            })
        return jsonify(transactions_list), 200
    except Exception as e:
        print (f"Error fetching transactions: {e}")
        return jsonify({'message':'Failed to fetch financial data', 'status':'error'}), 500

@mpesa_bp.route("/c2b/confirmation", methods=["POST"])
def c2b_confirmation():
    # 1. Receive the JSON payload from M-Pesa
    try:
        mpesa_data = request.get_json()
        if not mpesa_data:
            return jsonify({"ResultCode":"0","ResultDesc":"Invalid payload"}), 200
    except Exception as e:
        print(f"Validation: error parsing JSON: {e}")
        return jsonify({"ResultCode": 0, "ResultDesc": "Internal server error"}), 200

    # 2. Extract key transaction details from the payload
    transaction_id = mpesa_data.get('TransID')
    transaction_time = mpesa_data.get('TransTime')
    transacted_amount = mpesa_data.get('TransAmount')
    shortcode = mpesa_data.get('BillRefNumber')
    payer_phone_number = mpesa_data.get('MSISDN')
    
    #use shortcode to find the corresponding agents user_id
    agent_integration = MpesaIntegration.query.filter_by(shortcode=shortcode).first()
    if not agent_integration:
        print(f"Confirmation failed: No agent found for shortcode{shortcode}")
        return jsonify({"ResultCode":"0", "ResultDesc":"Success"}), 200

    agent_user_id = agent_integration.user_id

    try:
        new_transaction = MpesaTransactions(
            user_id=agent_user_id,
            mpesa_trans_id=transaction_id,
            amount=transacted_amount,
            transaction_time=transaction_time,
            account_reference=shortcode,
            phone_number=payer_phone_number
        )
        db.session.add(new_transaction)
        db.session.commit()
    except Exception as e:
        print(f"Failed to save transaction to database: {e}")
    
    # 5. Acknowledge the request to M-Pesa
    # The response body MUST be in this specific JSON format.
    # A 200 OK status code is essential. M-Pesa will not retry
    # if you return a status code outside of 200.
    return jsonify({
        "ResultCode": "0",
        "ResultDesc": "Confirmation received successfully"
    }), 200

@mpesa_bp.route("/c2b/validation", methods=["POST"])
def c2b_validation():
    try:
        mpesa_data = request.get_json()
        if not mpesa_data:
            return jsonify({"ResultCode": "1", "ResultDesc":"Invalid payload"}), 200
    except Exception as e:
        print(f"Error parsing JSON from M-Pesa: {e}")
        # A 200 OK status is crucial here, as M-Pesa expects a response.
        # However, a non-zero ResultCode in the JSON payload will reject the transaction.
        return jsonify({"ResultCode": "1", "ResultDesc": "An internal server error occurred."}), 200

    # 2. Extract key details for validation
    transacted_amount = mpesa_data.get('TransAmount')
    shortcode = mpesa_data.get('BillRefNumber')
    payer_phone_number = mpesa_data.get('MSISDN')

    agent_integration = MpesaIntegration.query.filter_by(shortcode=shortcode).first()
    if not agent_integration:
        print(f"Validation failed: No agent found for shortcode {shortcode}.")
        return jsonify({
            "ResultCode":"C2B00012",
            "ResultDesc":"The provided account number (Paybill) is not registered with our system."
        }), 200

    print(f"Validation successful for transaction to account {account_number}.")
    return jsonify({
        "ResultCode": "0",
        "ResultDesc": "Accepted"
    }), 200