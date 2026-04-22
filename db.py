import firebase_admin
from firebase_admin import credentials, firestore

# 1. Connect to the Firebase Vault using your Master Key
# (Ensure your 'firebase_key.json' file is inside the same folder as this file!)
cred = credentials.Certificate("firebase_key.json")

# Prevent the server from crashing if it reloads and tries to initialize twice
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

# 2. Get the database instance
db = firestore.client()

def get_user(user_uid):
    """Fetches the user from Firebase to check their credits"""
    user_ref = db.collection('users').document(user_uid)
    doc = user_ref.get()
    
    if doc.exists:
        return doc.to_dict()
    else:
        return None

# We keep this old function name so your app.py doesn't immediately crash!
def get_or_create_user(user_uid):
    return get_user(user_uid)

def deduct_credit(user_uid):
    """Subtracts 1 credit from the user after a successful AI generation"""
    user_ref = db.collection('users').document(user_uid)
    user_ref.update({
        "free_credits": firestore.Increment(-1)
    })