import requests
import os
from dotenv import load_dotenv

load_dotenv()

NESSIE_API_KEY = os.getenv('NESSIE_API_KEY')
BASE_URL = 'http://api.nessieisreal.com'

def get_all_customers():
    """Get all customers"""
    url = f'{BASE_URL}/customers?key={NESSIE_API_KEY}'
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

def get_customer(customer_id):
    """Get customer details"""
    url = f'{BASE_URL}/customers/{customer_id}?key={NESSIE_API_KEY}'
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

def get_customer_accounts(customer_id):
    """Get all accounts for a customer"""
    url = f'{BASE_URL}/customers/{customer_id}/accounts?key={NESSIE_API_KEY}'
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

def get_account(account_id):
    """Get account details"""
    url = f'{BASE_URL}/accounts/{account_id}?key={NESSIE_API_KEY}'
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

def get_account_purchases(account_id):
    """Get all purchases for an account"""
    url = f'{BASE_URL}/accounts/{account_id}/purchases?key={NESSIE_API_KEY}'
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

def get_account_deposits(account_id):
    """Get all deposits for an account"""
    url = f'{BASE_URL}/accounts/{account_id}/deposits?key={NESSIE_API_KEY}'
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

def get_account_withdrawals(account_id):
    """Get all withdrawals for an account"""
    url = f'{BASE_URL}/accounts/{account_id}/withdrawals?key={NESSIE_API_KEY}'
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

def create_purchase(account_id, merchant_id, medium, amount, description=""):
    """Create a purchase transaction"""
    url = f'{BASE_URL}/accounts/{account_id}/purchases?key={NESSIE_API_KEY}'
    data = {
        "merchant_id": merchant_id,
        "medium": medium,
        "purchase_date": "2024-02-07",
        "amount": amount,
        "description": description
    }
    response = requests.post(url, json=data)
    return response.json() if response.status_code == 201 else None

def create_deposit(account_id, medium, amount, description=""):
    """Create a deposit transaction"""
    url = f'{BASE_URL}/accounts/{account_id}/deposits?key={NESSIE_API_KEY}'
    data = {
        "medium": medium,
        "transaction_date": "2024-02-07",
        "amount": amount,
        "description": description
    }
    response = requests.post(url, json=data)
    return response.json() if response.status_code == 201 else None

def get_all_transactions(account_id):
    """Get all transactions (purchases, deposits, withdrawals) for an account"""
    transactions = []

    # Get purchases
    purchases = get_account_purchases(account_id)
    if purchases:
        for purchase in purchases:
            purchase['type'] = 'purchase'
            transactions.append(purchase)

    # Get deposits
    deposits = get_account_deposits(account_id)
    if deposits:
        for deposit in deposits:
            deposit['type'] = 'deposit'
            transactions.append(deposit)

    # Get withdrawals
    withdrawals = get_account_withdrawals(account_id)
    if withdrawals:
        for withdrawal in withdrawals:
            withdrawal['type'] = 'withdrawal'
            transactions.append(withdrawal)

    return transactions
