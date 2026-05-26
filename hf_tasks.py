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
HF_TOKEN = os.getenv('HF_TOKEN') 
HF_API_URL = "https://vaniconnect-vaniconnect-api.hf.space/api/remove-video-watermark" 

# 4️⃣ FIREBASE SETUP
if not firebase_admin._apps:
    key_path = "/etc/secrets/firebase_key.json" if os.path.exists("/etc/secrets/firebase_key.json") else "firebase_key.json"
    cred = credentials.Certificate(key_path)
    firebase_admin.initialize_app(cred)
firestore_db = firestore.client()

# ---------------------------------------------------------
# 🚀 THE MAIN QUEUE FUNCTION
# ---------------------------------------------------------
def run_hf_watermark_removal(job_data):
    user_id = job_data['user_id']
    r2_file_key = job_data['r2_file_key']
    
    print(f"🚀 [WORKER] Starting job for User {user_id}. Fetching: {r2_file_key}")

    # Step 1: Download raw video into Linux temporary space
    local_input_path = f"/tmp/worker_raw_{os.path.basename(r2_file_key)}"
    s3.download_file(bucket_name, r2_file_key, local_input_path)
    print("✅ [WORKER] Downloaded video from R2.")

    # Step 2: Forward payload to Hugging Face GPU Cluster
    print("🧠 [WORKER] Sending video to Hugging Face GPU... (This might take a few minutes)")
    headers = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}
    
    with open(local_input_path, "rb") as f:
        response = requests.post(
            HF_API_URL, 
            headers=headers, 
            files={"file": f},
            data={
                "user_id": user_id,
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
    local_output_path = f"/tmp/worker_clean_{os.path.basename(r2_file_key)}"
    with open(local_output_path, "wb") as f:
        f.write(response.content)
    print("✅ [WORKER] Success! Received clean video from Hugging Face.")

    # Step 4: Convert Video Container to Web-Safe H.264 Codec for Chrome compatibility
    # Extract just the raw filename without folder structures safely
    pure_filename = os.path.basename(r2_file_key)
    web_safe_output_path = f"/tmp/web_{pure_filename}"
    
    print(f"🎬 [WORKER] Converting video tracks to H.264 (Web Standard)... Input: {local_output_path} -> Output: {web_safe_output_path}")
    
    # Force FFmpeg to use absolute, verified paths on the Linux disk
    os.system(f'ffmpeg -y -i "{local_output_path}" -vcodec libx264 -pix_fmt yuv420p -acodec aac "{web_safe_output_path}"')

    # Step 5: Push normalized asset back to Cloudflare R2
    final_r2_key = f"completed/clean_{pure_filename}"
    
    # VERIFICATION CHECK: If FFmpeg fails or skips, fallback safely to the original clean video so it never crashes!
    upload_target = web_safe_output_path if os.path.exists(web_safe_output_path) else local_output_path
    print(f"☁️ [WORKER] Uploading finalized file to R2 path: {upload_target}")

    with open(upload_target, 'rb') as f:
        s3.put_object(Bucket=bucket_name, Key=final_r2_key, Body=f)
    print(f"☁️ [WORKER] Upload complete: {final_r2_key}")
    
    # Step 6: Dispatch live webhook tracking state to Firestore
    job_ref = firestore_db.collection('users').document(user_id).collection('processed_videos').document()
    job_ref.set({
        "status": "completed",
        "original_file": r2_file_key,
        "final_file_url": f"{os.getenv('R2_PUBLIC_DOMAIN')}/{final_r2_key}", 
        "tool": "video-watermark",
    })
    print(f"🎉 [WORKER] Job complete! Notified Firebase.")

    # Step 7: Clear operational cache from storage drive to keep Render clean
    try:
        if os.path.exists(local_input_path): os.remove(local_input_path)
        if os.path.exists(local_output_path): os.remove(local_output_path)
        if os.path.exists(web_safe_output_path): os.remove(web_safe_output_path)
        print("🧹 [WORKER] Temporary operational files scrubbed.")
    except Exception as e:
        print(f"⚠️ [WORKER] Cache scrubbing notice: {str(e)}")

    return True