# models.py
from extensions import db
from cryptography.fernet import Fernet
import os

# Generate a single encryption key and store it securely
# DO NOT hardcode this in your code. Use a .env file or a secret manager.
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY') or Fernet.generate_key().decode()

cipher_suite = Fernet(ENCRYPTION_KEY.encode())

class MpesaIntegration(db.Model):
    __tablename__ = 'mpesa_integrations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), unique=True, nullable=False)
    shortcode = db.Column(db.String(255), nullable=False)
    
    # Store encrypted keys
    encrypted_consumer_key = db.Column(db.LargeBinary, nullable=False)
    encrypted_consumer_secret = db.Column(db.LargeBinary, nullable=False)
    encrypted_passkey = db.Column(db.LargeBinary, nullable=False)
    
    # New columns to track registration status
    is_registered = db.Column(db.Boolean, default=False)
    registration_response = db.Column(db.JSON)

    def __init__(self, user_id, shortcode, consumer_key, consumer_secret, passkey):
        self.user_id = user_id
        self.shortcode = shortcode
        # Encrypt data before storing
        self.encrypted_consumer_key = cipher_suite.encrypt(consumer_key.encode())
        self.encrypted_consumer_secret = cipher_suite.encrypt(consumer_secret.encode())
        self.encrypted_passkey = cipher_suite.encrypt(passkey.encode())
    
    # Helper properties to decrypt keys when needed
    @property
    def consumer_key(self):
        return cipher_suite.decrypt(self.encrypted_consumer_key).decode()
    
    @property
    def consumer_secret(self):
        return cipher_suite.decrypt(self.encrypted_consumer_secret).decode()

    @property
    def passkey(self):
        return cipher_suite.decrypt(self.encrypted_passkey).decode()

class MpesaTransactions(db.Model):
    __tablename__ = 'mpesa_transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), nullable=False)
    mpesa_trans_id = db.Column(db.String(255), unique=True, nullable=False)
    amount = db.Column(db.Numeric(10,2), nullable=False)
    transaction_time = db.Column(db.String(255), nullable=False)
    account_reference = db.Column(db.String(255), nullable=True)
    phone_number = db.Column(db.String(255), nullable=True)