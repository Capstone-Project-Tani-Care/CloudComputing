from firebase_admin import firestore
from .userModel import get_user_by_uid
import uuid

db = firestore.client()

# Threads
def save_thread_to_firestore(thread_id, body, owner_id, created_at, photo_url=None):
    """Save a thread to Firestore."""
    thread_data = {
        'id': thread_id,
        'body': body,
        'createdAt': created_at,
        'ownerId': owner_id,
        'upVotes': 0,
        'totalComments': 0,
        'photoUrl': photo_url,
    }
    db.collection('threads').document(thread_id).set(thread_data)
    return thread_data

def get_all_threads(limit=10, page=1):
    """
    Fetch all threads from Firestore with pagination.
    """
    threads_ref = db.collection('threads').order_by('createdAt', direction=firestore.Query.DESCENDING).limit(limit).offset((page - 1) * limit).stream()
    threads = [doc.to_dict() for doc in threads_ref]

    # Fetch user details for each thread
    for thread in threads:
        user = get_user_by_uid(thread['ownerId'])
        thread['username'] = user.get('name')
        thread['photoProfileUrl'] = user.get('profile_photo')

    return threads

def get_thread_by_id(thread_id):
    """Retrieve a specific thread by its ID."""
    doc = db.collection('threads').document(thread_id).get()
    if doc.exists:
        thread = doc.to_dict()
        user = get_user_by_uid(thread['ownerId'])
        thread['username'] = user.get('name')
        thread['photoProfileUrl'] = user.get('profile_photo')
        return thread
    return None

def count_upvotes_by_thread_id(thread_id):
    """Count the number of upvotes for a specific thread."""
    upvotes_ref = db.collection('upvotes').where('threadId', '==', thread_id).stream()
    return sum(1 for _ in upvotes_ref)

# Comments
def save_comment_to_firestore(thread_id, content, owner, created_at):
    """Save a comment to Firestore and update the thread's comment count."""
    comment_id = f"comment-{uuid.uuid4()}"
    comment_data = {
        'id': comment_id,
        'content': content,
        'threadId': thread_id,
        'createdAt': created_at,
        'owner': owner,
    }
    db.collection('comments').document(comment_id).set(comment_data)

    # Increment the total comment count in the thread document
    thread_ref = db.collection('threads').document(thread_id)
    thread_ref.update({'totalComments': firestore.Increment(1)})

    return comment_data

def get_comments_by_thread_id(thread_id):
    """Retrieve all comments for a specific thread."""
    comments_ref = db.collection('comments').where('threadId', '==', thread_id).stream()
    return [doc.to_dict() for doc in comments_ref]

# Upvotes
def save_upvote_to_firestore(thread_id, user_id):
    """Save an upvote to Firestore and update the thread's upvote count."""
    # Check if the user has already upvoted the thread
    if check_if_user_upvoted(thread_id, user_id):
        raise ValueError("User has already upvoted this thread")

    thread_ref = db.collection('threads').document(thread_id)
    thread = thread_ref.get()
    if not thread.exists:
        raise ValueError("Thread not found")

    thread_data = thread.to_dict()
    upvotes = thread_data.get('upVotes', 0) + 1

    # Save the upvote
    upvote_data = {
        'threadId': thread_id,
        'userId': user_id,
        'voteType': 1  # 1 for upvote
    }
    db.collection('upvotes').add(upvote_data)

    # Update the upvote count in the thread document
    thread_ref.update({'upVotes': upvotes})
    return upvotes

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
    upvotes = [doc.to_dict() for doc in upvotes_ref]
    user_ids = [upvote['userId'] for upvote in upvotes]
    return user_ids

def remove_upvote_from_firestore(thread_id, user_id):
    """Remove an upvote from Firestore and update the thread's upvote count."""
    # Find the upvote document
    upvote_query = db.collection('upvotes') \
        .where('threadId', '==', thread_id) \
        .where('userId', '==', user_id) \
        .limit(1) \
        .stream()

    upvote_docs = list(upvote_query)
    if not upvote_docs:
        raise ValueError("Upvote not found")

    # Delete the upvote document
    upvote_doc = upvote_docs[0]
    db.collection('upvotes').document(upvote_doc.id).delete()

    # Decrement the upvote count in the thread document
    thread_ref = db.collection('threads').document(thread_id)
    thread = thread_ref.get()
    if not thread.exists:
        raise ValueError("Thread not found")

    thread_data = thread.to_dict()
    upvotes = thread_data.get('upVotes', 0) - 1
    if upvotes < 0:
        upvotes = 0

    thread_ref.update({'upVotes': upvotes})
    return upvotes

def check_if_user_upvoted(thread_id, user_id):
    """Check if a user has already upvoted a thread."""
    upvote_query = db.collection('upvotes') \
        .where('threadId', '==', thread_id) \
        .where('userId', '==', user_id) \
        .limit(1) \
        .stream()
    return any(upvote_query)
