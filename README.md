# # *TANICARE Cloud Computing*
---
## 🌱 **Project Overview**
Welcome to **Tanicare**, an innovative mobile application developed to help farmers diagnose plant diseases using cutting-edge machine learning technology. This project is our final submission for **Bangkit Academy 2024 Batch 2**, and it’s aimed at boosting agricultural productivity by making plant disease diagnosis faster, easier, and more reliable.

---

## 👨‍💻 **Team Profile**
**Team ID**: **C242-PS022**

### Meet the brilliant minds behind **Tanicare**:
- **(ML)** M296B4KY3909 – Rizki Baehtiar Afandi – *Universitas Pembangunan Nasional Veteran Jawa Timur* 
- **(ML)** M296B4KY0474 – Anak Agung Ngurah Wisnu Wardana – *Universitas Pembangunan Nasional Veteran Jawa Timur* 
- **(ML)** M296B4KY0876 – Bryan Anantha Manggala Pranaja Hartono – *Universitas Pembangunan Nasional Veteran Jawa Timur*   
- **(CC)** C296B4KY2692 – Muhammad Afrian Nur Setiawansyah – *Universitas Pembangunan Nasional Veteran Jawa Timur* 
- **(CC)** C296B4KY2873 – Muhammad Hakan Syakur – *Universitas Pembangunan Nasional Veteran Jawa Timur*  
- **(MD)** A296B4KY1279 – Erlangga Putra Ramadhan – *Universitas Pembangunan Nasional Veteran Jawa Timur*  
- **(MD)** A296B4KY4355 – Titis Fajar Nurdiansyah – *Universitas Pembangunan Nasional Veteran Jawa Timur*  

### **Roles/Responsibilities**
- **Project Planning**: Erlangga Putra Ramadhan, Titis Fajar Nurdiansyah, Rizki Baehtiar Afandi, Anak Agung Ngurah Wisnu Wardana, Bryan Anantha Manggala Pranaja Hartono, Muhammad Afrian Nur Setiawansyah, Muhammad Hakan Syakur  
- **UI/UX**: Erlangga Putra Ramadhan, Titis Fajar Nurdiansyah  
- **Machine Learning Model Development**: Rizki Baehtiar Afandi, Anak Agung Ngurah Wisnu Wardana, Bryan Anantha Manggala Pranaja Hartono  
- **Android App Development**: Erlangga Putra Ramadhan, Titis Fajar Nurdiansyah  
- **Deployment**: Muhammad Afrian Nur Setiawansyah, Muhammad Hakan Syakur  

---

## 🌾 **Project Background**
Agriculture is the backbone of Indonesia's economy, yet crop diseases pose a major threat to food security. The Tanicare project aims to solve the challenge of timely disease detection in crops like rice, cassava, tomatoes, corn, and soy by providing a mobile solution powered by machine learning. Our app allows farmers to upload photos of affected crops and instantly receive disease predictions, helping to prevent crop failures and improve overall crop quality.

---

## ⚙️ **Solution**
- **Machine Learning**: Detect plant diseases in rice, cassava, tomatoes, corn, and soy using pre-trained models.  
- **Android App**: Intuitive mobile interface for disease detection through images.  
- **Cloud Integration**: Real-time data processing and prediction results.  
- **User-Friendly**: Simple interaction through image input, result feedback, and history tracking.  

---


## 🌾 *Project Cloud Computing*
Architecture

![Untitled Diagram (1)](https://github.com/user-attachments/assets/2cf0f82a-2ddf-4532-9bda-f238d689d301)

---

## 📁 *API Documentation*
> Base url of this service is: http://localhost:4000/
- Authentications
  <pre>POST  /signup</pre>
  <pre>POST  /login</pre>
  <pre>POST  /refresh-token</pre>
  <pre>PUT   /account/update-email</pre>
  <pre>PUT   /account/update-password</pre>
  
- User
  <pre>GET   /profile</pre>
  <pre>POST  /profile/photo</pre>
  <pre>PUT   /edit-profile/name</pre>
  <pre>GET   /edit-profile/location</pre>
  <pre>PUT   /edit-profile/location-by-name</pre>
  <pre>POST  /edit-profile/about</pre>

- Disease Predictions
  <pre>POST  /prediction/potato</pre>
  <pre>POST  /prediction/corn</pre>
  <pre>POST  /prediction/rice</pre>
  <pre>POST  /prediction/soybean</pre>
  <pre>POST  /prediction/tomato</pre>

- Weather Prediction
  <pre>GET   /region_name</pre>
  <pre>GET   /region_code?</pre>

- Thread
  <pre>POST  /threads</pre>
  <pre>GET   /threads fetch</pre>
  <pre>GET   /threadsid</pre>
  <pre>POST  /bookmarks</pre>
  <pre>GET   /bookmarks</pre>
  <pre>DEL   /bookmarks</pre>
  <pre>POST  /comments</pre>
  <pre>GET   /comments</pre>
  <pre>POST  /up-vote</pre>
  <pre>GET   /threads/threads_id/upvotes</pre>
  <pre>DEL   /up-vote</pre>

---

## Environment

In order to run this project, you need to configure the following environment variables:
```bash
# Initialize Firebase Admin SDK
cred = credentials.Certificate('your firebase credential key')
firebase_admin.initialize_app(cred)

# Firebase Web API Key 
API_KEY = '{your firebase API key}'
        
# Utility functions for Google Cloud Storage
def get_gcs_client():
    return storage.Client.from_service_account_json("your bucket credential key")
```
