from firebase_admin import firestore

db = firestore.client()

def save_user_to_firestore(uid, email, name):
    user_data = {
        'uid': uid,
        'email': email,
        'name': name,
    }
    db.collection('users').document(uid).set(user_data)

def get_user_by_uid(uid):
    doc = db.collection('users').document(uid).get()
    if doc.exists:
        return doc.to_dict()
    else:
        return None
