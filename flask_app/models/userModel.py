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

def save_user_photo(uid, photo_url):

    user_ref = db.collection('users').document(uid)
    user_ref.update({'profile_photo': photo_url})

def get_user_profile(uid):

    user_ref = db.collection('users').document(uid)
    doc = user_ref.get()
    if doc.exists:
        return doc.to_dict()
    return None

def update_user_location(uid, kode_wilayah, region_name):

    user_ref = db.collection('users').document(uid)
    user_ref.update({
        'location': kode_wilayah,
        'region_name': region_name  # Save readable region name
    })

def add_created_thread_to_user(uid, thread_id):

    user_ref = db.collection('users').document(uid)
    user_ref.update({
        'created_threads': firestore.ArrayUnion([thread_id])  # Add thread_id to the array without duplicates
    })
