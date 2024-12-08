import os
import json
import numpy as np
from PIL import Image
from flask import Flask, request, jsonify
from auth.firebase_auth import create_user, verify_user, get_user_by_uid_and_get_details, login_user, get_user_by_uid, update_user_email, update_user_password, update_user_display_name, refresh_id_token
from models.userModel import save_user_to_firestore, get_user_by_uid, get_user_profile, save_user_photo, update_user_location, add_created_thread_to_user
from models.threadmodel import (
    save_thread_to_firestore,
    get_thread_by_id,
    save_comment_to_firestore,
    get_comments_by_thread_id,
    save_upvote_to_firestore,
    check_if_user_upvoted,
    get_upvotes_by_thread_id,
    get_all_threads,
    remove_upvote_from_firestore
)
from firebase_admin import firestore
from werkzeug.utils import secure_filename
from google.cloud import storage
from utils.tflite_model import load_tflite_model_from_gcs, run_tflite_inference, load_class_names
from utils.image_preprocess import preprocess_image
from models.wilayah_lookup import load_all_regions, suggest_regions_by_name, get_codes_by_name, find_name_by_code
import requests
import uuid

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
            return jsonify({'error': True, 'message': 'Email and password are required'}), 400

        # Get credentials from request
        email = data['email']
        password = data['password']

        # Authenticate user and get tokens
        auth_result = login_user(email, password)
        
        return jsonify({
            'error': False,
            'message': 'Login successful',
            'userId': auth_result['uid'],
            'idToken': auth_result['idToken'],
            'refreshToken': auth_result['refreshToken']
        }), 200

    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 400

@app.route('/refresh-token', methods=['POST'])
def refresh_token():
    try:
        refresh_token = request.json.get('refreshToken')
        if not refresh_token:
            return jsonify({'error': True, 'message': 'Refresh token is required'}), 400
        
        tokens = refresh_id_token(refresh_token)
        return jsonify({'status': 'success', 'data': tokens}), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/account/update-email', methods=['PUT'])
def update_email():
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        user = get_user_by_uid_and_get_details(token.split(' ')[1])
        data = request.json
        new_email = data.get('email')

        if not new_email:
            return jsonify({'error': True, 'message': 'New email is required'}), 400

        # Update email in Firebase Auth
        update_user_email(user['uid'], new_email)
        
        # Update email in Firestore
        user_ref = db.collection('users').document(user['uid'])
        user_ref.update({'email': new_email})

        return jsonify({
            'status': 'success',
            'message': 'Email updated successfully',
            'data': {'uid': user['uid'], 'email': new_email}
        }), 200

    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/account/update-password', methods=['PUT'])
def update_password():
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        user = get_user_by_uid_and_get_details(token.split(' ')[1])
        data = request.json
        new_password = data.get('password')

        if not new_password:
            return jsonify({'error': True, 'message': 'New password is required'}), 400

        # Update password in Firebase Auth
        update_user_password(user['uid'], new_password)

        return jsonify({
            'status': 'success',
            'message': 'Password updated successfully'
        }), 200

    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/bookmarks', methods=['POST'])
def create_bookmark():
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        user = get_user_by_uid_and_get_details(token.split(' ')[1])
        data = request.json
        thread_id = data.get('threadId')

        if not thread_id:
            return jsonify({'error': True, 'message': 'Thread ID is required'}), 400

        # Check if thread exists
        thread = get_thread_by_id(thread_id)
        if not thread:
            return jsonify({'error': True, 'message': 'Thread not found'}), 404

        # Check if already bookmarked
        existing_bookmark = db.collection('bookmarks') \
            .where('userId', '==', user['uid']) \
            .where('threadId', '==', thread_id) \
            .limit(1) \
            .stream()

        if any(existing_bookmark):
            return jsonify({'error': True, 'message': 'Thread already bookmarked'}), 400

        # Create bookmark
        bookmark_data = {
            'userId': user['uid'],
            'threadId': thread_id,
            'createdAt': firestore.SERVER_TIMESTAMP
        }
        db.collection('bookmarks').add(bookmark_data)

        return jsonify({'status': 'success', 'message': 'Bookmark created successfully'}), 201

    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/bookmarks', methods=['GET'])
def get_user_bookmarks():
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        user = get_user_by_uid_and_get_details(token.split(' ')[1])

        # Get all bookmarks for the user
        bookmarks_ref = db.collection('bookmarks') \
            .where('userId', '==', user['uid']) \
            .stream()
        
        bookmarks = []
        for bookmark in bookmarks_ref:
            bookmark_data = bookmark.to_dict()
            # Get thread details
            thread = get_thread_by_id(bookmark_data['threadId'])
            if thread:
                bookmarks.append({
                    'threadId': thread['id'],
                    'ownerId': thread['ownerId']
                })

        return jsonify({
            'status': 'success',
            'message': 'Bookmarks retrieved successfully',
            'data': bookmarks
        }), 200

    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/bookmarks/<thread_id>', methods=['DELETE'])
def remove_bookmark(thread_id):
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        user = get_user_by_uid_and_get_details(token.split(' ')[1])

        # Find and delete the bookmark
        bookmark_ref = db.collection('bookmarks') \
            .where('userId', '==', user['uid']) \
            .where('threadId', '==', thread_id) \
            .limit(1) \
            .get()

        if len(bookmark_ref) == 0:
            return jsonify({'error': True, 'message': 'Bookmark not found'}), 404

        # Delete the bookmark
        bookmark_ref[0].reference.delete()

        return jsonify({
            'status': 'success',
            'message': 'Bookmark removed successfully'
        }), 200

    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/profile', methods=['GET'])
def get_profile():
    """
    Get user profile details based on userId.
    """
    try:
        # Get userId from query parameters
        user_id_param = request.args.get('userId')

        if not user_id_param:
            return jsonify({'error': True, 'message': 'userId parameter is required'}), 400

        # Fetch profile from Firestore using the provided userId
        profile = get_user_profile(user_id_param)
        if not profile:
            return jsonify({'error': True, 'message': 'Profile not found'}), 404

        # Return profile details
        return jsonify({
            'status': 'success',
            'data': {
                'name': profile.get('name'),
                'location': profile.get('location'),
                'about': profile.get('about'),
                'profile_photo': profile.get('profile_photo'),
                'region_name': profile.get('region_name'),
                'created_threads': profile.get('created_threads')
            }
        }), 200

    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/profile/photo', methods=['POST'])
def upload_profile_photo():
    """
    Upload or update the user's profile photo.
    """
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        # Verify the user and get UID
        user = get_user_by_uid_and_get_details(token.split(' ')[1])
        uid = user['uid']

        # Check if a photo is uploaded
        if 'photo' not in request.files:
            return jsonify({'error': True, 'message': 'No photo uploaded'}), 400

        photo = request.files['photo']
        if not photo:
            return jsonify({'error': True, 'message': 'Invalid photo file'}), 400

        # Save photo temporarily
        filename = secure_filename(photo.filename)
        temp_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        photo.save(temp_file_path)

        # Upload photo to GCS
        photo_url = upload_to_bucket(GCS_BUCKET_NAME, temp_file_path, f"profile_photos/{uid}/{filename}")
        os.remove(temp_file_path)

        # Update Firestore with the new photo URL
        save_user_photo(uid, photo_url)

        return jsonify({
            'status': 'success',
            'message': 'Profile photo updated successfully',
            'data': {'profile_photo': photo_url}
        }), 200

    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

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

@app.route('/edit-profile/location', methods=['GET'])
def get_location_by_code():
    """
    Get location name based on kode wilayah and save to Firestore.
    """
    try:
        # Ambil token autentikasi
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        # Verifikasi user dan dapatkan UID
        user = get_user_by_uid_and_get_details(token.split(' ')[1])
        uid = user['uid']

        # Ambil kode wilayah dari parameter query
        kode_wilayah = request.args.get('kode_wilayah')
        if not kode_wilayah:
            return jsonify({'error': True, 'message': 'kode_wilayah parameter is required'}), 400

        # Cari nama wilayah di CSV berdasarkan kode wilayah
        matching_region = find_name_by_code(all_regions, kode_wilayah)
        if not matching_region:
            return jsonify({'error': True, 'message': f'No region found for kode_wilayah: {kode_wilayah}'}), 404

        # Ambil nama daerah
        region_name = matching_region['name']

        # Simpan lokasi ke Firestore
        update_user_location(uid, kode_wilayah, region_name)

        return jsonify({
            'status': 'success',
            'message': 'Location updated successfully',
            'data': {
                'uid': uid,
                'kode_wilayah': kode_wilayah,
                'region_name': region_name
            }
        }), 200

    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/edit-profile/location', methods=['PUT'])
def update_location_by_code():
    """
    Update location in Firestore based on kode wilayah input.
    """
    try:
        # Ambil token autentikasi
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        # Verifikasi user dan dapatkan UID
        user = get_user_by_uid_and_get_details(token.split(' ')[1])
        uid = user['uid']

        # Ambil kode wilayah dari request body
        data = request.json
        kode_wilayah = data.get('kode_wilayah')
        if not kode_wilayah:
            return jsonify({'error': True, 'message': 'kode_wilayah is required'}), 400

        # Cari nama wilayah di CSV berdasarkan kode wilayah
        matching_region = find_name_by_code(all_regions, kode_wilayah)
        if not matching_region:
            return jsonify({'error': True, 'message': f'No region found for kode_wilayah: {kode_wilayah}'}), 404

        # Ambil nama daerah
        region_name = matching_region['name']

        # Update lokasi di Firestore
        update_user_location(uid, kode_wilayah, region_name)

        return jsonify({
            'status': 'success',
            'message': 'Location updated successfully',
            'data': {
                'uid': uid,
                'kode_wilayah': kode_wilayah,
                'region_name': region_name
            }
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
            return jsonify({'error': True, 'message': 'body is required'}), 400
        
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

        # Generate a unique thread ID
        thread_id = f"thread-{uuid.uuid4()}"
        created_at = firestore.SERVER_TIMESTAMP

        # Save thread to Firestore
        thread = save_thread_to_firestore(
            thread_id=thread_id,
            body=body,
            owner_id=user['uid'],
            created_at=created_at,
            photo_url=photo_url,
        )

        # Tambahkan thread_id ke data user di Firestore
        add_created_thread_to_user(user['uid'], thread_id)

        # Retrieve saved thread with resolved timestamp
        saved_thread = db.collection('threads').document(thread_id).get().to_dict()

        return jsonify({
            'status': 'success',
            'message': 'Thread created',
            'data': {'thread': saved_thread}
        }), 201

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/threads', methods=['GET'])
def fetch_threads():
    """
    Fetch threads with pagination. Optionally fetch a single thread by thread_id.
    """
    try:
        thread_id = request.args.get('thread_id')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))

        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        user = get_user_by_uid_and_get_details(token.split(' ')[1])
        uid = user['uid']

        if thread_id:
            thread = get_thread_by_id(thread_id)
            if not thread:
                return jsonify({'error': True, 'message': f'Thread with ID {thread_id} not found'}), 404
            return jsonify({'status': 'success', 'data': {'thread': thread}}), 200

        threads = get_all_threads(limit=limit, page=page)
        return jsonify({'status': 'success', 'data': {'threads': threads}}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
        data = request.json

@app.route('/comments', methods=['POST'])
def create_comment():
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        user = get_user_by_uid_and_get_details(token.split(' ')[1])
        user_id = user['uid']
        data = request.json
        thread_id = data.get('threadId')
        content = data.get('content')

        if not thread_id or not content:
            return jsonify({'error': True, 'message': 'Thread ID and content are required'}), 400

        created_at = firestore.SERVER_TIMESTAMP
        owner = {
            'id': user_id,
            'name': user['name']
        }

        comment = save_comment_to_firestore(thread_id, content, owner, created_at)

        return jsonify({'status': 'success', 'message': 'Comment created', 'data': {'comment': comment}}), 201

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/comments', methods=['GET'])
def get_comments():
    try:
        thread_id = request.args.get('threadId')
        if not thread_id:
            return jsonify({'error': True, 'message': 'threadId is required'}), 400

        # Query comments by threadId
        comments = get_comments_by_thread_id(thread_id)

        return jsonify({
            'status': 'success',
            'message': 'Comments retrieved',
            'data': {'comments': comments}
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/threads/<thread_id>/upvote', methods=['POST'])
def upvote_thread(thread_id):
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        user = get_user_by_uid_and_get_details(token.split(' ')[1])
        user_id = user['uid']

        try:
            upvotes = save_upvote_to_firestore(thread_id, user_id)
            return jsonify({'status': 'success', 'data': {'upvotes': upvotes}}), 200
        except ValueError as e:
            return jsonify({'error': True, 'message': str(e)}), 400

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
import requests

@app.route('/threads/<thread_id>/upvotes', methods=['GET'])
def get_upvotes(thread_id):
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        user = get_user_by_uid_and_get_details(token.split(' ')[1])
        user_id = user['uid']

        user_ids = get_upvotes_by_thread_id(thread_id)
        return jsonify({'status': 'success', 'data': {'userIds': user_ids}}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/up-vote/<thread_id>', methods=['DELETE'])
def remove_upvote(thread_id):
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': True, 'message': 'Authorization token is required'}), 401

        user = get_user_by_uid_and_get_details(token.split(' ')[1])
        user_id = user['uid']

        upvotes = remove_upvote_from_firestore(thread_id, user_id)
        return jsonify({'status': 'success', 'data': {'upvotes': upvotes}}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Load treatment data
with open('./utils/treatments.json') as f:
    TREATMENTS = json.load(f)

CLASS_NAMES = load_class_names()
BUCKET_NAME = "tanicare"

@app.route('/predict/<plant>', methods=['POST'])
def predict_disease(plant):
    """
    Predict plant disease and return detailed prediction results with treatment.
    """
    try:
        if plant not in TREATMENTS:
            return jsonify({'error': True, 'message': f'Unsupported plant type: {plant}'}), 400

        if plant not in CLASS_NAMES:
            return jsonify({'error': True, 'message': f'No class definitions for plant type: {plant}'}), 400

        if 'image' not in request.files:
            return jsonify({'error': True, 'message': 'No image file provided'}), 400

        file = request.files['image']
        if not file:
            return jsonify({'error': True, 'message': 'Invalid image file'}), 400

        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_image_path)

        # Load the model
        model_name = f"{plant.capitalize()}.tflite"
        interpreter = load_tflite_model_from_gcs(BUCKET_NAME, model_name)

        # Preprocess the image
        input_data = preprocess_image(temp_image_path, target_size=(150, 150))

        # Run inference and get predictions
        predictions = run_tflite_inference(interpreter, input_data)

        # Get prediction details
        predicted_class_idx = np.argmax(predictions)
        prediction_probabilities = {}
        
        # Get class names for the plant
        plant_classes = CLASS_NAMES[plant.lower()]
        
        # Calculate probabilities for each class
        for idx, prob in enumerate(predictions):
            if idx in plant_classes:
                class_name = plant_classes[idx]
                prediction_probabilities[class_name] = float(prob)

        predicted_class_name = plant_classes.get(predicted_class_idx, "Unknown")
        treatment = TREATMENTS[plant].get(predicted_class_name, "No treatment information available.")

        # Clean up temporary files
        os.remove(temp_image_path)

        return jsonify({
            'status': 'success',
            'message': 'Prediction completed',
            'data': {
                'plant': plant,
                'predicted_class': predicted_class_name,
                'treatment': treatment,
            }
        }), 200

    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

WILAYAH_FILEPATH = "data/base.csv"
all_regions = load_all_regions(WILAYAH_FILEPATH)

@app.route('/region_name', methods=['GET'])
def get_suggestions_by_name():
    """
    Suggest regions based on name matching.
    """
    try:
        query = request.args.get('query')
        if not query:
            return jsonify({'error': True, 'message': 'Query parameter is required'}), 400

        # Get matching regions (limited to 10 results)
        suggestions = suggest_regions_by_name(all_regions, query)
        if not suggestions:
            return jsonify({'status': 'success', 'message': 'No matches found', 'data': []}), 200

        return jsonify({'status': 'success', 'data': suggestions}), 200

    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/region_code', methods=['GET'])
def get_codes_by_region_name():
    """
    Get region codes by searching with region name.
    """
    try:
        query = request.args.get('query')
        if not query:
            return jsonify({'error': True, 'message': 'Query parameter is required'}), 400

        # Get matching region codes
        matching_codes = get_codes_by_name(all_regions, query)
        if not matching_codes:
            return jsonify({'status': 'success', 'message': 'No matches found', 'data': []}), 200

        return jsonify({'status': 'success', 'data': matching_codes}), 200

    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True, host='0.0.0.0', port=8080)
