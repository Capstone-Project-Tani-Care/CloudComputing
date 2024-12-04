from firebase_admin import firestore

db = firestore.client()

def save_user_to_firestore(uid, email, name, location=None):
#Save user details to Firestore, including location."""
    user_data = {
        'uid': uid,
        'email': email,
        'name': name,
        'location': location  # Save location if available
    }
    db.collection('users').document(uid).set(user_data)


def get_user_by_uid(uid):
    doc = db.collection('users').document(uid).get()
    if doc.exists:
        return doc.to_dict()
    else:
        return None

def update_user_location(uid, latitude, longitude):
    user_ref = db.collection('users').document(uid)
    user_ref.update({
        'location': {
            'latitude': latitude,
            'longitude': longitude
        }
    })