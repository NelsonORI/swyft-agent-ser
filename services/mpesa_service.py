import base64
import requests

def get_access_token(consumer_key, consumer_secret):
    api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    credentials = f"{consumer_key}:{consumer_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode('utf-8')

    headers = {'Authorization': f'Basic {encoded_credentials}'}
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    return response.json().get('access_token')

def register_mpesa_urls(access_token, shortcode, validation_url, confirmation_url):
    api_url = "https://sandbox.safaricom.co.ke/mpesa/c2b/v1/registerurl"
    headers = {'Content-Type': 'application/json','Authorization': f'Bearer {access_token}'}
    payload = {
        "ShortCode": shortcode,
        "ResponseType": "Completed",
        "ConfirmationURL": confirmation_url,
        "ValidationURL": validation_url
    }
    response = requests.post(api_url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()
