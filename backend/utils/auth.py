import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
import os

SECRET_KEY = os.getenv('JWT_SECRET', 'your-secret-key-change-this')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password, hashed_password):
    """Verify a password against its hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data):
    """Create a JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token):
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def jwt_required(f):
    """Decorator to protect routes with JWT authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None

        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({"error": "Invalid authorization header format"}), 401

        if not token:
            return jsonify({"error": "Authentication token is missing"}), 401

        # Verify token
        payload = decode_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401

        # Add user_id to request context
        request.user_id = payload.get("user_id")

        return f(*args, **kwargs)

    return decorated_function
