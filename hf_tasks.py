import os
import boto3
import requests
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# 1️⃣ LOAD ENVIRONMENT SECRETS
load_dotenv()

# 2️⃣ CLOUDFLARE R2 SYSTEM CONFIGURATION
s3 = boto3.client(
    's3',
    endpoint_url=os.getenv('R2_ENDPOINT_URL'),
    aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
    region_name='auto'
)
bucket_name = os.getenv('R2_BUCKET_NAME')

# 3️⃣ HUGGING FACE API SETUP
HF_TOKEN = os.getenv('HF_TOKEN') 
HF_API_URL = "https://vaniconnect-vaniconnect-api.hf.space/api/remove-video-watermark" 

# 4️⃣ FIREBASE ENTERPRISE INITIALIZATION
if not firebase_admin._apps:
    key_path = "/etc/secrets/firebase_key.json" if os.path.exists("/etc/secrets/firebase_key.json") else "firebase_key.json"
    cred = credentials.Certificate(key_path)
    firebase_admin.initialize_app(cred)
firestore_db = firestore.client()

# ---------------------------------------------------------
# 🚀 CORE QUEUE WORKER EXECUTION
# ---------------------------------------------------------
def run_hf_watermark_removal(job_data):
    user_id = job_data['user_id']
    r2_file_key = job_data['r2_file_key']
    
    print(f"🚀 [WORKER] Task initialized for User {user_id}. Fetching: {r2_file_key}")

    # STEP 1: Pull raw video from Cloudflare R2 into Linux storage space
    local_input_path = f"/tmp/worker_raw_{os.path.basename(r2_file_key)}"
    try:
        s3.download_file(bucket_name, r2_file_key, local_input_path)
        print("✅ [WORKER] Downloaded raw asset from R2 storage partition.")
    except Exception as r2_err:
        print(f"❌ [WORKER] Cloudflare R2 download breakdown: {str(r2_err)}")
        return False

    # STEP 2: Submit raw payload to Hugging Face API Gateway
    print("🧠 [WORKER] Transporting stream container to Hugging Face GPU Matrix...")
    headers = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}
    
    try:
        response = requests.post(
            HF_API_URL, 
            headers=headers, 
            files={"file": open(local_input_path, "rb")},
            data={
                "user_id": user_id,
                "mode": job_data['mode'], 
                "x": job_data['x'], 
                "y": job_data['y'], 
                "w": job_data['w'], 
                "h": job_data['h']
            }
        )
    except Exception as hf_api_err:
        print(f"❌ [WORKER] Failed to communicate with Hugging Face cluster: {str(hf_api_err)}")
        return False
    
    print(f"📡 [WORKER] Hugging Face HTTP Status: {response.status_code}")
    print(f"📡 [WORKER] Data Header Payload: {response.headers.get('Content-Type')}")

    if response.status_code != 200:
        print(f"❌ [WORKER] Model Pipeline Return Error Code {response.status_code}: {response.text}")
        return False

   # STEP 3: Handle JSON Parsing and Link Extraction safely
    local_output_path = f"/tmp/worker_clean_{os.path.basename(r2_file_key)}"
    
    try:
        response_data = response.json()
        print(f"📄 [WORKER] Decoded API Payload Array: {response_data}")
        
        hf_video_url = response_data.get('url') or response_data.get('video') or response_data.get('file')
        
        if not hf_video_url and 'file_name' in response_data:
            filename_clean = response_data['file_name']
            
            # Remove any trailing structural paths to stay safe
            filename_clean = filename_clean.replace("file=", "").replace("file/", "")
            
            # FORCE THE CORRECT PUBLIC DIRECT URL PATH STRING
            hf_video_url = f"https://vaniconnect-vaniconnect-api.hf.space/file/{filename_clean}"
        
        print(f"🔗 [WORKER] Direct download path target: {hf_video_url}")
    except Exception as json_err:
        print(f"❌ [WORKER] Content mismatch. Expected JSON format but engine failed to parse response payload: {str(json_err)}")
        return False
    
    # STEP 4: Download binary data stream from Hugging Face storage host link
    print(f"📥 [WORKER] Syncing video stream from Hugging Face storage cluster...")
    try:
        video_file_res = requests.get(hf_video_url, stream=True)
        if video_file_res.status_code == 200:
            with open(local_output_path, "wb") as f:
                for chunk in video_file_res.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
            print("✅ [WORKER] Video binary array written to local temp block disk storage safely.")
        else:
            print(f"❌ [WORKER] Storage server rejected video file pull with status: {video_file_res.status_code}")
            return False
    except Exception as download_err:
        print(f"❌ [WORKER] Video file down-stream pipe breakdown: {str(download_err)}")
        return False

    # STEP 5: Push finalized clean asset back to Cloudflare R2 Space
    pure_filename = os.path.basename(r2_file_key)
    final_r2_key = f"completed/clean_{pure_filename}"
    print(f"☁️ [WORKER] Dispatching clear file output path to R2 partition: {local_output_path}")

    try:
        with open(local_output_path, 'rb') as f:
            s3.put_object(Bucket=bucket_name, Key=final_r2_key, Body=f, ContentType='video/mp4')
        print(f"☁️ [WORKER] Storage upload process confirmed structural success: {final_r2_key}")
    except Exception as r2_upload_err:
        print(f"❌ [WORKER] Cloudflare storage upload block error: {str(r2_upload_err)}")
        return False
    
    # STEP 6: Inform Firestore Instance of Completion Link State
    try:
        job_ref = firestore_db.collection('users').document(user_id).collection('processed_videos').document()
        job_ref.set({
            "status": "completed",
            "original_file": r2_file_key,
            "final_file_url": f"{os.getenv('R2_PUBLIC_DOMAIN')}/{final_r2_key}", 
            "tool": "video-watermark",
        })
        print(f"🎉 [WORKER] Operational sequence success! Notified Firestore document listener pipelines.")
    except Exception as db_err:
        print(f"❌ [WORKER] Database entry transaction write failure: {str(db_err)}")
        return False

    # STEP 7: Flush Local Processing Memory Drives
    try:
        if os.path.exists(local_input_path): os.remove(local_input_path)
        if os.path.exists(local_output_path): os.remove(local_output_path)
        print("扫 [WORKER] Temp space disk sectors wiped.")
    except Exception as e:
        print(f"⚠️ [WORKER] Cache scrub operation log tracking: {str(e)}")

    return True 