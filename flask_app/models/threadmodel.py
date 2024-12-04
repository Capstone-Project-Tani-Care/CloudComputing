from firebase_admin import firestore

db = firestore.client()

# Threads
def save_thread_to_firestore(thread_id, body, owner_id, created_at, photo_url=None):
    """Save a thread to Firestore."""
    thread_data = {
        'id': thread_id,
        'body': body,
        'createdAt': created_at,
        'ownerId': owner_id,
        'upVotesBy': [],
        'totalComments': 0,
        'photoUrl': photo_url,
    }
    db.collection('threads').document(thread_id).set(thread_data)
    return thread_data

def get_all_threads():
    """
    Fetch all threads from Firestore.
    """
    threads_ref = db.collection('threads').stream()
    return [doc.to_dict() for doc in threads_ref]

def get_thread_by_id(thread_id):
    """Retrieve a specific thread by its ID."""
    doc = db.collection('threads').document(thread_id).get()
    if doc.exists:
        return doc.to_dict()
    return None

# Comments
def save_comment_to_firestore(comment_id, thread_id, content, owner, created_at):
    """Save a comment to Firestore."""
    comment_data = {
        'id': comment_id,
        'content': content,
        'threadId': thread_id,
        'createdAt': created_at,
        'owner': owner,
        'upVotesBy': [],
    }
    db.collection('comments').document(comment_id).set(comment_data)
    return comment_data

def get_comments_by_thread_id(thread_id):
    """Retrieve all comments for a specific thread."""
    comments_ref = db.collection('comments').where('threadId', '==', thread_id).stream()
    return [doc.to_dict() for doc in comments_ref]

# Upvotes
def save_upvote_to_firestore(upvote_id, thread_id, user_id):
    """Save an upvote to Firestore."""
    upvote_data = {
        'id': upvote_id,
        'threadId': thread_id,
        'userId': user_id,
        'voteType': 1  # 1 for upvote
    }
    db.collection('upvotes').document(upvote_id).set(upvote_data)
    return upvote_data

def check_if_user_upvoted(thread_id, user_id):
    """Check if a user has already upvoted a thread."""
    upvote_query = db.collection('upvotes') \
        .where('threadId', '==', thread_id) \
        .where('userId', '==', user_id) \
        .stream()
    return any(upvote_query)

def get_upvotes_by_thread_id(thread_id):
    """Retrieve all upvotes for a specific thread."""
    upvotes_ref = db.collection('upvotes').where('threadId', '==', thread_id).stream()
    return [doc.to_dict() for doc in upvotes_ref]
