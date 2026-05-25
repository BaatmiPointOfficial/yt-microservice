import os
import boto3
import requests
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# 1️⃣ LOAD SECRETS
load_dotenv()

# 2️⃣ CLOUDFLARE R2 SETUP
s3 = boto3.client(
    's3',
    endpoint_url=os.getenv('R2_ENDPOINT_URL'),
    aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
    region_name='auto'
)
bucket_name = os.getenv('R2_BUCKET_NAME')

# 3️⃣ HUGGING FACE SETUP
HF_TOKEN = os.getenv('HF_TOKEN') # You will need to add this to Render Environment Variables!
# Replace this URL with your actual Hugging Face Space API endpoint
HF_API_URL = "https://vaniconnect-vaniconnect-api.hf.space" 

# 4️⃣ FIREBASE SETUP (So the worker can update the database)
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred)
firestore_db = firestore.client()

# ---------------------------------------------------------
# 🚀 THE MAIN QUEUE FUNCTION
# ---------------------------------------------------------
def run_hf_watermark_removal(job_data):
    user_id = job_data['user_id']
    r2_file_key = job_data['r2_file_key']
    
    print(f"🚀 [WORKER] Starting job for User {user_id}. Fetching: {r2_file_key}")

    # Step 1: Download the raw video from Cloudflare R2
    local_input_path = f"downloads/worker_raw_{os.path.basename(r2_file_key)}"
    s3.download_file(bucket_name, r2_file_key, local_input_path)
    print("✅ [WORKER] Downloaded video from R2.")

    # Step 2: Send to Hugging Face API
    print("🧠 [WORKER] Sending video to Hugging Face GPU... (This might take a few minutes)")
    
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # We send the file and the parameters (x, y, width, height) to your AI model
    with open(local_input_path, "rb") as f:
        response = requests.post(
            HF_API_URL, 
            headers=headers, 
            files={"file": f},
            data={
                "mode": job_data['mode'], 
                "x": job_data['x'], 
                "y": job_data['y'], 
                "w": job_data['w'], 
                "h": job_data['h']
            }
        )
    
    if response.status_code != 200:
        print(f"❌ [WORKER] Hugging Face Error: {response.text}")
        return False

    # Step 3: Save the clean video returning from Hugging Face
    local_output_path = f"downloads/worker_clean_{os.path.basename(r2_file_key)}"
    with open(local_output_path, "wb") as f:
        f.write(response.content)
    print("✅ [WORKER] Success! Received clean video from Hugging Face.")

    # Step 4: Upload the finished video BACK to Cloudflare R2
    final_r2_key = f"completed/clean_{os.path.basename(r2_file_key)}"
    with open(local_output_path, 'rb') as f:
        s3.put_object(Bucket=bucket_name, Key=final_r2_key, Body=f)
    print(f"☁️ [WORKER] Uploaded clean video to R2: {final_r2_key}")
    
    # Step 5: Notify Firebase! 
    # Your React frontend should listen to this document to know when to show the download button
    job_ref = firestore_db.collection('users').document(user_id).collection('processed_videos').document()
    job_ref.set({
        "status": "completed",
        "original_file": r2_file_key,
        "final_file_url": f"{os.getenv('R2_PUBLIC_DOMAIN')}/{final_r2_key}", # Your public R2 domain
        "tool": "video-watermark",
    })

    print(f"🎉 [WORKER] Job complete! Notified Firebase.")

    # Step 6: Clean up local files to save server memory
    os.remove(local_input_path)
    os.remove(local_output_path)

    return True