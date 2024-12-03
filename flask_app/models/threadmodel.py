from firebase_admin import firestore

db = firestore.client()

def save_thread_to_firestore(thread_id, title, body, category, owner_id, created_at):
#Save a thread to Firestore."""
    thread_data = {
        'id': thread_id,
        'title': title,
        'body': body,
        'category': category,
        'createdAt': created_at,
        'ownerId': owner_id,
        'upVotesBy': [],
        'downVotesBy': [],
        'totalComments': 0
    }
    db.collection('threads').document(thread_id).set(thread_data)
    return thread_data

def get_all_threads():
#Retrieve all threads from Firestore."""
    threads_ref = db.collection('threads')
    return [doc.to_dict() for doc in threads_ref.stream()]

def get_thread_by_id(thread_id):
#Retrieve a specific thread by its ID."""
    doc = db.collection('threads').document(thread_id).get()
    if doc.exists:
        return doc.to_dict()
    return None

def save_comment_to_thread(thread_id, comment_id, content, owner, created_at):
#Save a comment to a specific thread."""
    comment_data = {
        'id': comment_id,
        'content': content,
        'createdAt': created_at,
        'upVotesBy': [],
        'downVotesBy': [],
        'owner': owner
    }
    db.collection('threads').document(thread_id).collection('comments').document(comment_id).set(comment_data)
    return comment_data

def get_comments_by_thread_id(thread_id):
#Retrieve all comments for a specific thread."""
    comments_ref = db.collection('threads').document(thread_id).collection('comments')
    return [doc.to_dict() for doc in comments_ref.stream()]
