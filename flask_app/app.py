from flask import Flask, request, jsonify
from auth.firebase_auth import create_user, verify_user, login_user
from firebase_admin import auth
from models.userModel import save_user_to_firestore, get_user_by_uid

app = Flask(__name__)

@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.json
        if not data or 'email' not in data or 'password' not in data or 'name' not in data:
            return jsonify({
                'error': True,
                'message': 'Email, password and name are required'
            }), 400

        email = data['email']
        password = data['password']
        name = data['name']

        # Create user in Firebase Auth
        uid = create_user(email, password, name)

        # Save user to Firestore
        save_user_to_firestore(uid, email, name)

        # Generate token for the new user
        custom_token = auth.create_custom_token(uid)
        
        return jsonify({
            'error': False,
            'message': 'User created successfully',
            'signupResult': {
                'userId': uid,
                'name': name,
                'token': custom_token.decode()
            }
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
        
        # Get user details from Firestore
        user = get_user_by_uid(auth_result['uid'])
        if not user:
            return jsonify({
                'error': True,
                'message': 'User not found'
            }), 404

        return jsonify({
            'error': False,
            'message': 'success',
            'loginResult': {
                'userId': user['uid'],
                'name': user['name'],
                'token': auth_result['token']
            }
        }), 200

    except Exception as e:
        return jsonify({
            'error': True,
            'message': str(e)
        }), 400


@app.route('/logout', methods=['POST'])
def logout():
    try:
        # For stateless API, logout is client-side (invalidate token locally)
        return jsonify({'message': 'Logout successful'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
