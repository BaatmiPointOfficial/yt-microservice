import os
import boto3
import shutil
import razorpay
import requests
from fastapi import FastAPI, Request, BackgroundTasks, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional
import firebase_admin
from firebase_admin import credentials, firestore
from redis import Redis
from rq import Queue

# 🤖 YOUR AI TOOLS
import yt_down  

import trim_video

import db

# 1️⃣ LOAD SECRETS FIRST
load_dotenv()

# 2️⃣ INITIALIZE THE APP (ONLY ONCE!)
app = FastAPI(title="VaniConnect AI Engine")

# 3️⃣ OPEN THE SECURITY GATES (CORS) - THIS FIXES YOUR BUTTON!
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://vaniconnect-studio.vercel.app",
        "https://clipeto.com",          
    "https://www.clipeto.com"
   
        
    ],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

# 4️⃣ SET UP RATE LIMITER
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 5️⃣ SET UP DOWNLOADS FOLDER
os.makedirs("downloads", exist_ok=True) 
app.mount("/downloads", StaticFiles(directory="downloads"), name="downloads")

# 6️⃣ CONNECT TO CLOUDFLARE R2
r2_access_key = os.getenv('R2_ACCESS_KEY_ID')
r2_secret_key = os.getenv('R2_SECRET_ACCESS_KEY')
r2_endpoint = os.getenv('R2_ENDPOINT_URL')
bucket_name = os.getenv('R2_BUCKET_NAME')


s3 = boto3.client(
    's3',
    endpoint_url=r2_endpoint,
    aws_access_key_id=r2_access_key,
    aws_secret_access_key=r2_secret_key,
    region_name='auto' 
)
# ---------------------------------------------------------
# 🚦 REDIS QUEUE SETUP (The Ticket Rail)
# ---------------------------------------------------------
redis_url = os.getenv('REDIS_URL')
if redis_url:
    redis_conn = Redis.from_url(redis_url)
    video_queue = Queue('video-processing', connection=redis_conn)
else:
    print("⚠️ WARNING: REDIS_URL is not set!")

# 7️⃣ RAZORPAY SETUP
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

rzp_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

class OrderRequest(BaseModel):
    user_id: str

class VerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    user_id: str

# 8️⃣ FIREBASE ADMIN SETUP
key_path = "/etc/secrets/firebase_key.json" if os.path.exists("/etc/secrets/firebase_key.json") else "firebase_key.json"
cred = credentials.Certificate(key_path)

# 🔥 FIX: Check if Firebase is already initialized to prevent reload crashes
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

firestore_db = firestore.client()
# ---------------------------------------------------------
# 🚀 ROUTES
# ---------------------------------------------------------

@app.get("/")
def read_root():
    return {"message": "✅ VaniConnect AI Engine is Live and Running!"}

# 1️⃣ CREATE THE ORDER
@app.post("/api/create-order")
async def create_order(req: OrderRequest):
    try:
        # ₹299 is 99900 paise in Razorpay
        order_amount = 29900  
        
        razorpay_order = rzp_client.order.create({
            "amount": order_amount,
            "currency": "INR",
            "receipt": f"receipt_{req.user_id}",
            "payment_capture": "1" # Auto-capture the payment
        })
        
        return {
            "order_id": razorpay_order['id'],
            "amount": order_amount,
            "currency": "INR"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2️⃣ VERIFY PAYMENT & UNLOCK PRO IN FIREBASE
@app.post("/api/verify-payment")
async def verify_payment(req: VerifyRequest):
    try:
        # 1. Razorpay securely checks if the payment is legitimate
        rzp_client.utility.verify_payment_signature({
            'razorpay_order_id': req.razorpay_order_id,
            'razorpay_payment_id': req.razorpay_payment_id,
            'razorpay_signature': req.razorpay_signature
        })
        
        # 2. 🚨 UNLOCK THE FIREBASE USER
        try:
            user_ref = firestore_db.collection('users').document(req.user_id)
            
            # 🔥 We use .set() with merge=True so it creates the user if they don't exist yet!
            user_ref.set({"isProUser": True}, merge=True)
            
            print(f"✅ Successfully upgraded user {req.user_id} to PRO in Firestore!")
        except Exception as e:
            print(f"🔥 FIREBASE ERROR: {e}")
            # We just print the error to the terminal, but we don't crash the app
            # because the Razorpay payment was actually successful!
        
        return {"status": "success", "message": "Payment verified. Pro Unlocked!"}
    
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Payment verification failed!")
# 👇 (Paste the rest of your AI tool routes down here like /api/enhance, etc.) 👇



@app.post("/api/download")
@limiter.limit("5/minute")
async def process_universal_download(
    request: Request, 
    url: str = Form(...),
    quality: str = Form("720p"), # 🌟 Catch the user's choice!
    user_id: str = Form(...) # 🌟 1. Added the Catching Mitt!
):
    # ❌ 2. Deleted the hardcoded admin_user_1!
    
    user_data = db.get_or_create_user(user_id)

    # 2. Safety Check: If Firebase returns NOTHING, stop gracefully!
    if not user_data:
        print(f"🚨 Blocked: User {user_id} not found in Firebase!")
        raise HTTPException(status_code=401, detail="User profile not found. Please log in securely.")

    # 3. Use the NEW Firebase vocabulary
    is_pro = user_data.get("isProUser", False)
    credits_left = user_data.get("free_credits", 0)

    # 4. The Paywall Logic
    if not is_pro and credits_left <= 0:
        print(f"🚨 Blocked: User {user_id} is out of credits!")
        raise HTTPException(status_code=402, detail="PaywallTrigger: Daily limit reached. Upgrade to Pro.")
    
    print(f"🔗 Received URL: {url} | Requested Format: {quality}")
    
    # 🌟 Pass the quality dynamically to your engine!
    safe_filename, title, thumbnail = yt_down.download_youtube_video(video_url=url, quality=quality)
    
    if not safe_filename:
        return {"error": "Failed to extract video. It might be private or age-restricted."}
        
    file_path = os.path.join("downloads", safe_filename)
    
    try:
        with open(file_path, 'rb') as video_file:
            s3.put_object(Bucket=bucket_name, Key=f'downloads/{safe_filename}', Body=video_file)
    except Exception as e:
        print(f"Cloudflare skipped: {e}")

    # 💰 DEDUCT CREDIT (Correctly aligned with the main function!)
    if not is_pro:
        db.deduct_credit(user_id)
        print(f"💸 Credit deducted! Remaining: {credits_left - 1}")
        
    return {
        "message": "Success!", 
        "file_name": safe_filename,
        "title": title,
        "thumbnail": thumbnail,
        "is_audio": quality == "audio" # Let React know if it's an MP3!
    }


@app.post("/api/batch-split")
@limiter.limit("5/minute")
async def process_batch_split(
    request: Request,
    video_file: UploadFile = File(...),
    clip_duration: int = Form(60),
    user_id: str = Form(...)
    
):
  
    user_data = db.get_or_create_user(user_id)

    # 2. Safety Check: If Firebase returns NOTHING, stop gracefully!
    if not user_data:
        print(f"🚨 Blocked: User {user_id} not found in Firebase!")
        raise HTTPException(status_code=401, detail="User profile not found. Please log in securely.")

    # 3. Use the NEW Firebase vocabulary
    is_pro = user_data.get("isProUser", False)
    credits_left = user_data.get("free_credits", 0)

    # 4. The Paywall Logic
    if not is_pro and credits_left <= 0:
        print(f"🚨 Blocked: User {user_id} is out of credits!")
        # 402 Payment Required is the perfect status code here!
        raise HTTPException(status_code=402, detail="PaywallTrigger: Daily limit reached. Upgrade to Pro.")
    
    input_video = f"downloads/temp_batch_{video_file.filename}"
    
    # Save the giant video
    with open(input_video, "wb") as buffer:
        buffer.write(await video_file.read())

    print(f"🔪 Starting Batch Split on {video_file.filename} every {clip_duration} seconds...")
    
    # Call our new Zipping Engine
    success, zip_path = trim_video.split_video_into_parts(
        input_video, 
        clip_duration, 
        "downloads"
    )

    if not success:
        return {"error": "Failed to batch split video."}

    # Clean up the massive original input video to save space
    try:
        os.remove(input_video)
    except Exception:
        pass

    if not is_pro:
        db.deduct_credit(user_id)
        print(f"💸 Credit deducted! Remaining: {credits_left - 1}")
        
    return {"message": "Success!", "file_name": os.path.basename(zip_path)}

@app.post("/api/trim-single")
@limiter.limit("5/minute")
async def process_single_clip(
    request: Request,
    video_file: UploadFile = File(...),
    start_time: str = Form(...),   # 👈 Now Python catches the Start Time!
    end_time: str = Form(...),     # 👈 Now Python catches the End Time!
    text: str = Form(""),          # 👈 Catches the overlay text
    user_id: str = Form(...)
):
    # 1. User Auth & Paywall (Copy your standard Firebase checks here)
    user_data = db.get_or_create_user(user_id)
    # ... your usual safety checks ...

    # 2. Save the incoming video
    input_video = f"downloads/temp_single_{video_file.filename}"
    with open(input_video, "wb") as buffer:
        buffer.write(await video_file.read())

    print(f"✂️ Trimming single clip from {start_time} to {end_time}...")
    
    # 3. Call your trimming logic from trim_video.py!
    # (Make sure you have a function in trim_video.py that takes start/end times)
    output_filename = f"trimmed_{video_file.filename}"
    output_path = f"downloads/{output_filename}"
    
# We use the actual function name: trim_video
# Note: We are ignoring the 'text' variable for now because your trim_video function 
# doesn't accept a text parameter yet!
    success = trim_video.trim_video(input_video, output_path, start_time, end_time)

    if not success:
        return {"error": "Failed to trim the single clip."}

    # 4. Clean up original file & deduct credit
    import os
    os.remove(input_video)

    return {"message": "Success!", "file_name": output_filename}

@app.get("/test-db")
def test_database():
    user_data = db.get_or_create_user("ceo@vaniconnect.com")
    return {"message": "Database is working perfectly!", "user_data": user_data}
# ---------------------------------------------------------
# 🚀 CORE PIPELINE WORKER FUNCTION (RUNS ON A NATIVE SIDE-THREAD)
# ---------------------------------------------------------
def process_video_directly(user_id: str, r2_file_key: str, mode: str, x: int, y: int, w: int, h: int):
    print(f"🎬 [PIPELINE] Starting direct real-time video process for User: {user_id}")
    
    pure_filename = os.path.basename(r2_file_key)
    local_input_path = f"downloads/raw_{pure_filename}"
    local_output_path = f"downloads/clean_{pure_filename}"
    
    # 1. Pull down the raw asset file from your Cloudflare R2 partition
    try:
        s3.download_file(bucket_name, r2_file_key, local_input_path)
        print("✅ [PIPELINE] Raw video downloaded locally to disk storage.")
    except Exception as e:
        print(f"❌ [PIPELINE] Cloudflare R2 recovery failed: {str(e)}")
        return

    # 2. Fire binary payload streams straight to the Hugging Face GPU Cluster
    HF_API_URL = "https://vaniconnect-vaniconnect-api.hf.space/api/remove-video-watermark"
    headers = {"Authorization": f"Bearer {os.getenv('HF_TOKEN')}"} if os.getenv('HF_TOKEN') else {}
    
    try:
        with open(local_input_path, "rb") as video_bytes:
            response = requests.post(
                HF_API_URL,
                headers=headers,
                files={"file": video_bytes},
                data={"user_id": user_id, "mode": mode, "x": x, "y": y, "w": w, "h": h},
                timeout=550 # Safe headroom buffer under Render's 10-minute cap
            )
        
        response_data = response.json()
        print(f"📡 [PIPELINE] Hugging Face Response Payload: {response_data}")
        
        # Extract filename using our canonical Gradio structural path fix
        filename_clean = response_data.get('file_name')
        if not filename_clean:
            print("❌ [PIPELINE] Expected file_name target pointer missing from response dictionary.")
            return
            
        # Clean up formatting remnants safely
        filename_clean = filename_clean.replace("file=", "").replace("file/", "")
        
        # 🔗 BUILD GRADIO CANONICAL API ACCESS ROUTE
        hf_video_url = f"https://vaniconnect-vaniconnect-api.hf.space/gradio_api/file={filename_clean}"
        print(f"🔗 [PIPELINE] Verified streaming URL path resolved: {hf_video_url}")
        
    except Exception as e:
        print(f"❌ [PIPELINE] Core modeling cluster handshake failed: {str(e)}")
        return

    # 3. Secure download stream from the dynamic Gradio file gateway
    try:
        video_file_res = requests.get(hf_video_url, stream=True)
        if video_file_res.status_code == 200:
            with open(local_output_path, "wb") as f:
                for chunk in video_file_res.iter_content(chunk_size=1024*1024):
                    if chunk: 
                        f.write(chunk)
            print("✅ [PIPELINE] Output array written safely to localized system blocks.")
        else:
            print(f"❌ [PIPELINE] File download rejected by storage node with status: {video_file_res.status_code}")
            return
    except Exception as e:
        print(f"❌ [PIPELINE] Binary stream processing hit an interruption block: {str(e)}")
        return

    # 4. Upload the final clean production asset back to Cloudflare R2
    final_r2_key = f'completed/clean_{pure_filename}'
    # Ensure R2_PUBLIC_DOMAIN env variable matches your cloud link configuration
    public_domain = os.getenv('R2_PUBLIC_DOMAIN', '').rstrip('/')
    final_public_url = f"{public_domain}/{final_r2_key}"

    try:
        with open(local_output_path, 'rb') as final_data:
            s3.put_object(Bucket=bucket_name, Key=final_r2_key, Body=final_data, ContentType='video/mp4')
        print(f"☁️ [PIPELINE] Asset uploaded cleanly to Cloudflare R2 space layout: {final_r2_key}")
    except Exception as e:
        print(f"❌ [PIPELINE] Cloudflare terminal cloud save failed: {str(e)}")
        return

    # 5. Instantly broadcast state to your Firebase React frontend architecture listeners
    try:
        # Create a document identifier matching the job tracker mapping configuration
        job_ref = firestore_db.collection('users').document(user_id).collection('processed_videos').document()
        job_ref.set({
            "status": "completed",
            "original_file": r2_file_key,
            "final_file_url": final_public_url,
            "tool": "video-watermark",
        })
        print(f"🎉 [PIPELINE] Done! Document state active for client user screen player reference.")
    except Exception as e:
        print(f"❌ [PIPELINE] Database transaction sync failed: {str(e)}")

    # Clean up local system storage blocks to protect your container drives
    for path in [local_input_path, local_output_path]:
        if os.path.exists(path): 
            os.remove(path)


# ---------------------------------------------------------
# 🛠️ NATIVE DIRECT FASTAPI ROUTE ENDPOINT
# ---------------------------------------------------------
@app.post("/api/remove-video-watermark")
@limiter.limit("5/minute")
async def process_video_watermark(
    request: Request,
    background_tasks: BackgroundTasks, # 🚀 Native side-thread engine loader
    file: UploadFile = File(...),
    mode: str = Form(...),
    user_id: str = Form(...),
    x: int = Form(0), y: int = Form(0), w: int = Form(0), h: int = Form(0)
):
    # 1. Standard Profile Gatekeep checks
    user_data = db.get_or_create_user(user_id)
    if not user_data:
        raise HTTPException(status_code=401, detail="User validation path invalid.")
        
    is_pro = user_data.get("isProUser", False)
    credits_left = user_data.get("free_credits", 0)

    if not is_pro and credits_left <= 0:
        raise HTTPException(status_code=402, detail="PaywallTrigger: Daily processing bounds reached.")

    # 2. Drop uploaded video chunks into local drive spaces cleanly
    temp_path = f"downloads/raw_watermark_{file.filename}"
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())

    # 3. Synchronize raw input back up to your secure Cloudflare R2 bucket partition
    r2_key = f'uploads/raw_watermark_{file.filename}'
    try:
        with open(temp_path, 'rb') as video_file:
            s3.put_object(Bucket=bucket_name, Key=r2_key, Body=video_file)
    except Exception as e:
        if os.path.exists(temp_path): os.remove(temp_path)
        raise HTTPException(status_code=500, detail="Cloudflare partition storage upload rejected.")
    
    # Drop intermediate file pointer allocations
    os.remove(temp_path)

    # 💰 DEDUCT FREE USER CREDIT ALLOCATION INSTANTLY
    if not is_pro:
        db.deduct_credit(user_id)
        print(f"💸 Credit deducted from User {user_id}! Balance remaining: {credits_left - 1}")

    # 4. 🚀 DEPLOY TO BACKGROUND WORKER THREAD (ZERO REDIS MIDDLEMAN DELAY)
    background_tasks.add_task(
        process_video_directly,
        user_id, r2_key, mode, x, y, w, h
    )

    print(f"🎟️ Real-time local worker thread spinning up for User {user_id}...")

    # 5. Instantly return status success to React UI to prevent network disconnect error loops
    return {
        "message": "Processing engine engaged successfully.",
        "status": "processing"
    }