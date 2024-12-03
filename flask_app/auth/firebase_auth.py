import firebase_admin
from firebase_admin import credentials, auth, firestore
from firebase_admin._auth_utils import handle_auth_backend_error
import requests

# Initialize Firebase Admin SDK
cred = credentials.Certificate('auth/firebase-key.json.json')
firebase_admin.initialize_app(cred)

db = firestore.client()


# Helper for Firebase Authentication
def create_user(email, password, name):
    try:
        user = auth.create_user(email=email, password=password, display_name=name)
        return user.uid
    except Exception as e:
        raise ValueError(f"Error creating user: {str(e)}")

def verify_user(token):
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token['uid']
    except auth.InvalidIdTokenError:
        raise ValueError("Invalid authentication token.")
    except Exception as e:
        raise ValueError(f"Error verifying token: {str(e)}")

def verify_user_and_get_details(token):
    """Verify token and return user details."""
    try:
        uid = verify_user(token)
        user = get_user_by_uid(uid)
        if not user:
            raise ValueError("User not found in Firestore.")
        return user
    except Exception as e:
        raise ValueError(f"Error retrieving user details: {str(e)}")

def login_user(email, password):
    try:
        # Firebase Web API Key (you need to set this up in your Firebase Console)
        API_KEY = 'api_key'
        
        # Firebase Auth REST API endpoint for email/password sign-in
        url = f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}'
        
        payload = {
            'email': email,
            'password': password,
            'returnSecureToken': True
        }
        
        response = requests.post(url, json=payload)
        data = response.json()
        
        if response.status_code != 200:
            raise ValueError(data.get('error', {}).get('message', 'Authentication failed'))
            
        return {
            'uid': data['localId'],
            'token': data['idToken']
        }
        
    except Exception as e:
        raise ValueError(f"Login failed: {str(e)}")

# Helper to fetch user details from Firestore
def get_user_by_uid(uid):
    """Fetch user details from Firestore."""
    try:
        doc = db.collection('users').document(uid).get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        raise ValueError(f"Error fetching user details: {str(e)}")
