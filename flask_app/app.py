from flask import Flask, request, jsonify
from auth.firebase_auth import create_user, verify_user_and_get_details, login_user, get_user_by_uid
from models.userModel import save_user_to_firestore
from models.threadmodel import (
    save_thread_to_firestore,
    get_all_threads,
    get_thread_by_id,
    save_comment_to_thread,
    get_comments_by_thread_id,
)
from firebase_admin import firestore

app = Flask(__name__)
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

        # Save user to Firestore
        save_user_to_firestore(uid, email, name)

        return jsonify({
            'error': False,
            'message': 'User created successfully',
            'userId': uid,
            'name': name
        }), 201

    except Exception as e:
        return jsonify({
            'error': True,
            'message': str(e)
        }), 400


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
        return jsonify({
            'error': True,
            'message': str(e)
        }), 400


@app.route('/threads', methods=['POST'])
def create_thread():
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        user = verify_user_and_get_details(token.split(' ')[1])

        data = request.json
        title = data.get('title')
        body = data.get('body')
        category = data.get('category', 'General')

        if not title or not body:
            return jsonify({'error': True, 'message': 'Title and body are required'}), 400

        thread_id = f"thread-{user['uid'][:8]}"
        thread_data = {
            'id': thread_id,
            'title': title,
            'body': body,
            'category': category,
            'createdAt': firestore.SERVER_TIMESTAMP,
            'ownerId': user['uid'],
            'upVotesBy': [],
            'downVotesBy': [],
            'totalComments': 0,
        }

        # Save thread to Firestore
        db.collection('threads').document(thread_id).set(thread_data)

        # Retrieve the saved thread to include actual timestamp
        saved_thread = db.collection('threads').document(thread_id).get().to_dict()

        return jsonify({
            'status': 'success',
            'message': 'Thread created',
            'data': {'thread': saved_thread}
        }), 201

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/threads', methods=['GET'])
def get_threads():
    try:
        threads = get_all_threads()
        return jsonify({
            'status': 'success',
            'message': 'ok',
            'data': {'threads': threads}
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/threads/<thread_id>', methods=['GET'])
def get_thread_detail(thread_id):
    try:
        # Retrieve thread by ID
        thread = get_thread_by_id(thread_id)
        if not thread:
            return jsonify({'status': 'error', 'message': 'Thread not found'}), 404

        # Add comments and owner details
        owner = get_user_by_uid(thread['ownerId'])
        comments = get_comments_by_thread_id(thread_id)

        thread['owner'] = {
            'id': owner['uid'],
            'name': owner['name'],
            'avatar': owner.get('avatar', '')
        }
        thread['comments'] = comments

        return jsonify({
            'status': 'success',
            'message': 'ok',
            'data': {'detailThread': thread}
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/threads/<thread_id>/comments', methods=['POST'])
def create_comment(thread_id):
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        user = verify_user_and_get_details(token.split(' ')[1])

        data = request.json
        content = data.get('content')

        if not content:
            return jsonify({'error': True, 'message': 'Content is required'}), 400

        comment_id = f"comment-{user['uid'][:8]}"
        comment_data = {
            'id': comment_id,
            'content': content,
            'createdAt': firestore.SERVER_TIMESTAMP,
            'upVotesBy': [],
            'downVotesBy': [],
            'owner': {
                'id': user['uid'],
                'name': user['name'],
                'email': user.get('email', '')
            }
        }

        # Save comment to Firestore
        thread_ref = db.collection('threads').document(thread_id)
        thread_ref.collection('comments').document(comment_id).set(comment_data)

        # Retrieve the saved comment with populated fields
        saved_comment = thread_ref.collection('comments').document(comment_id).get().to_dict()

        return jsonify({
            'status': 'success',
            'message': 'Comment created',
            'data': {'comment': saved_comment}
        }), 201

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
