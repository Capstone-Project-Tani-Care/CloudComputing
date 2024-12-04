import os
import numpy as np
from PIL import Image
from flask import Flask, request, jsonify
from auth.firebase_auth import create_user, verify_user, get_user_by_uid_and_get_details, login_user, get_user_by_uid, update_user_email, update_user_password, update_user_display_name
from models.userModel import save_user_to_firestore, get_user_by_uid, update_user_location
from models.threadmodel import (
    save_thread_to_firestore,
    get_thread_by_id,
    save_comment_to_firestore,
    get_comments_by_thread_id,
    save_upvote_to_firestore,
    check_if_user_upvoted,
    get_upvotes_by_thread_id,
    get_all_threads
)
from firebase_admin import firestore
from werkzeug.utils import secure_filename
from google.cloud import storage
import requests

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "./uploads"
GCS_BUCKET_NAME = "tanicare-threads"

# Utility functions for Google Cloud Storage
def get_gcs_client():
    return storage.Client.from_service_account_json("bucket.json")

def upload_to_bucket(bucket_name, source_file_path, destination_blob_name):
    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    # Upload the file to the bucket
    blob.upload_from_filename(source_file_path)

    # Make the file publicly accessible
    blob.make_public()

    # Return the public URL
    return blob.public_url

db = firestore.client()

@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.json
        if not data or 'email' not in data or 'password' not in data or 'name' not in data:
            return jsonify({
                'error': True,
                'message': 'Email, password, and name are required'
            }), 400

        email = data['email']
        password = data['password']
        name = data['name']

        # Create user in Firebase Auth
        uid = create_user(email, password, name)

        # Save user to Firestore with location
        save_user_to_firestore(uid, email, name)

        return jsonify({
            'error': False,
            'message': 'User created successfully',
            'userId': uid,
            'name': name,
        }), 201

    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 400


@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({
                'error': True,
                'message': 'Email and password are required'
            }), 400

        # Get credentials from request
        email = data['email']
        password = data['password']

        # Authenticate user and get token
        auth_result = login_user(email, password)
        
        return jsonify({
            'error': False,
            'message': 'Login successful',
            'userId': auth_result['uid'],
            'token': auth_result['token']
        }), 200

    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 400

@app.route('/edit-profile/name', methods=['PUT'])
def update_name():
    """
    Update the user's name in Firestore.
    """
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        user_uid = get_user_by_uid_and_get_details(token.split(' ')[1])['uid']
        data = request.json
        name = data.get('name')

        if not name:
            return jsonify({'error': True, 'message': 'Name is required'}), 400

        # Update name in Firestore
        user_ref = db.collection('users').document(user_uid)
        user_ref.update({'name': name})

        return jsonify({
            'status': 'success',
            'message': 'Name updated successfully',
            'data': {'uid': user_uid, 'name': name}
        }), 200
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/edit-profile/location', methods=['PUT'])
def update_location():
    """
    Update the user's location in Firestore.
    """
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        user_uid = get_user_by_uid_and_get_details(token.split(' ')[1])['uid']
        data = request.json
        location = data.get('location')

        if not location:
            return jsonify({'error': True, 'message': 'Location is required'}), 400

        # Update location in Firestore
        user_ref = db.collection('users').document(user_uid)
        user_ref.update({'location': location})

        return jsonify({
            'status': 'success',
            'message': 'Location updated successfully',
            'data': {'uid': user_uid, 'location': location}
        }), 200
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/edit-profile/about', methods=['POST'])
def update_about():
    """
    Add or update the user's about section in Firestore.
    """
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        user_uid = get_user_by_uid_and_get_details(token.split(' ')[1])['uid']
        data = request.json
        about = data.get('about')

        if not about:
            return jsonify({'error': True, 'message': 'About section is required'}), 400

        # Update about in Firestore
        user_ref = db.collection('users').document(user_uid)
        user_ref.update({'about': about})

        return jsonify({
            'status': 'success',
            'message': 'About section updated successfully',
            'data': {'uid': user_uid, 'about': about}
        }), 200
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500


@app.route('/threads', methods=['POST'])
def create_thread():
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        user = get_user_by_uid_and_get_details(token.split(' ')[1])

        # Get thread data from request
        data = request.form
        body = data.get('body')

        if not body:
            return jsonify({'error': True, 'message': 'body are required'}), 400
        
        photo_url = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file:
                filename = secure_filename(file.filename)
                temp_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(temp_file_path)

                # Upload to GCS
                photo_url = upload_to_bucket(GCS_BUCKET_NAME, temp_file_path, f"threads/{filename}")
                os.remove(temp_file_path)

        thread_id = f"thread-{user['uid'][:8]}"
        created_at = firestore.SERVER_TIMESTAMP

        # Save thread to Firestore
        thread = save_thread_to_firestore(
            thread_id=thread_id,
            body=body,
            owner_id=user['uid'],
            created_at=created_at,
            photo_url=photo_url,
        )

        # Retrieve saved thread with resolved timestamp
        saved_thread = db.collection('threads').document(thread_id).get().to_dict()

        return jsonify({
            'status': 'success',
            'message': 'Thread created',
            'data': {'thread': saved_thread}
        }), 201

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
from flask import jsonify

@app.route('/threads', methods=['GET'])
def fetch_threads():
    """
    Fetch all threads from Firestore.
    """
    try:
        threads = get_all_threads()
        return jsonify({
            'status': 'success',
            'message': 'Threads fetched successfully',
            'data': threads
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/comments', methods=['POST'])
def create_comment():
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        user = get_user_by_uid_and_get_details(token.split(' ')[1])

        data = request.json
        thread_id = data.get('threadId')
        content = data.get('content')

        if not thread_id or not content:
            return jsonify({'error': True, 'message': 'threadId and content are required'}), 400

        comment_id = f"comment-{user['uid'][:8]}"
        created_at = firestore.SERVER_TIMESTAMP

        # Save comment to Firestore
        comment = {
            'id': comment_id,
            'content': content,
            'threadId': thread_id,
            'createdAt': created_at,
            'owner': {
                'id': user['uid'],
                'name': user['name']
            },
            'upVotesBy': [],
        }
        db.collection('comments').document(comment_id).set(comment)

        # Retrieve the saved comment
        saved_comment = db.collection('comments').document(comment_id).get().to_dict()

        return jsonify({
            'status': 'success',
            'message': 'Comment created',
            'data': {'comment': saved_comment}
        }), 201

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/comments', methods=['GET'])
def get_comments():
    try:
        thread_id = request.args.get('threadId')
        if not thread_id:
            return jsonify({'error': True, 'message': 'threadId is required'}), 400

        # Query comments by threadId
        comments_ref = db.collection('comments').where('threadId', '==', thread_id).stream()
        comments = [doc.to_dict() for doc in comments_ref]

        return jsonify({
            'status': 'success',
            'message': 'Comments retrieved',
            'data': {'comments': comments}
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/up-vote', methods=['POST'])
def upvote_thread():
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        user = get_user_by_uid_and_get_details(token.split(' ')[1])

        data = request.json
        thread_id = data.get('threadId')
        if not thread_id:
            return jsonify({'error': True, 'message': 'threadId is required'}), 400

        # Check if the user has already upvoted this thread
        upvote_query = db.collection('upvotes') \
            .where('threadId', '==', thread_id) \
            .where('userId', '==', user['uid']) \
            .stream()

        if any(upvote_query):
            return jsonify({'error': True, 'message': 'You have already upvoted this thread'}), 400

        upvote_id = f"upvote-{user['uid'][:8]}"
        upvote = {
            'id': upvote_id,
            'threadId': thread_id,
            'userId': user['uid'],
            'voteType': 1
        }
        db.collection('upvotes').document(upvote_id).set(upvote)

        return jsonify({
            'status': 'success',
            'message': 'Thread upvoted',
            'data': {'vote': upvote}
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/up-vote', methods=['GET'])
def get_upvotes():
    try:
        thread_id = request.args.get('threadId')
        if not thread_id:
            return jsonify({'error': True, 'message': 'threadId is required'}), 400

        # Query upvotes by threadId
        upvotes_ref = db.collection('upvotes').where('threadId', '==', thread_id).stream()
        upvotes = [doc.to_dict() for doc in upvotes_ref]

        return jsonify({
            'status': 'success',
            'message': 'Upvotes retrieved',
            'data': {'upvotes': upvotes}
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
import requests

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True, host='0.0.0.0', port=8080)
