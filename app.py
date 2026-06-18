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
import uuid
from fastapi import BackgroundTasks  # 🌟 Ensure this is added to your fastapi imports at the top!

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
# 🚦 REDIS QUEUE SETUP (Bypassed for real-time background tasks)
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

@app.head("/")
@app.get("/")
def read_root():
    return {"message": "✅ VaniConnect AI Engine is Live and Running!"}

# 1️⃣ CREATE THE ORDER
@app.post("/api/create-order")
async def create_order(req: OrderRequest):
    try:
        # ₹299 is 29900 paise in Razorpay
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
        
        return {"status": "success", "message": "Payment verified. Pro Unlocked!"}
    
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Payment verification failed!")

@app.post("/api/download")
@limiter.limit("5/minute")
async def process_universal_download(
    request: Request, 
    url: str = Form(...),
    quality: str = Form("720p"), 
    user_id: str = Form(...) 
):
    user_data = db.get_or_create_user(user_id)

    if not user_data:
        print(f"🚨 Blocked: User {user_id} not found in Firebase!")
        raise HTTPException(status_code=401, detail="User profile not found. Please log in securely.")

    is_pro = user_data.get("isProUser", False)
    credits_left = user_data.get("free_credits", 0)

    if not is_pro and credits_left <= 0:
        print(f"🚨 Blocked: User {user_id} is out of credits!")
        raise HTTPException(status_code=402, detail="PaywallTrigger: Daily limit reached. Upgrade to Pro.")
    
    print(f"🔗 Received URL: {url} | Requested Format: {quality}")
    
    safe_filename, title, thumbnail = yt_down.download_youtube_video(video_url=url, quality=quality)
    
    if not safe_filename:
        return {"error": "Failed to extract video. It might be private or age-restricted."}
        
    file_path = os.path.join("downloads", safe_filename)
    
    try:
        with open(file_path, 'rb') as video_file:
            s3.put_object(Bucket=bucket_name, Key=f'downloads/{safe_filename}', Body=video_file)
    except Exception as e:
        print(f"Cloudflare skipped: {e}")

    if not is_pro:
        db.deduct_credit(user_id)
        print(f"💸 Credit deducted! Remaining: {credits_left - 1}")
        
    return {
        "message": "Success!", 
        "file_name": safe_filename,
        "title": title,
        "thumbnail": thumbnail,
        "is_audio": quality == "audio" 
    }
import uuid
from fastapi import BackgroundTasks  # 🌟 Ensure this is added to your fastapi imports at the top!

# 🛰️ Global task tracker to store background job state
batch_tasks = {}

def background_split_task(input_video: str, clip_duration: int, user_id: str, is_pro: bool, task_id: str):
    """ Runs the heavy video slicing and zipping in the background outside the HTTP request timeline """
    try:
        print(f"📦 [Task {task_id}] Processing heavy video compression matrix...")
        success, zip_path = trim_video.split_video_into_parts(
            input_video, 
            clip_duration, 
            "downloads"
        )

        if success:
            print(f"✅ [Task {task_id}] Batch split complete! Asset archived safely.")
            batch_tasks[task_id] = {
                "status": "completed", 
                "file_name": os.path.basename(zip_path)
            }
            # Deduct credit only after guaranteed processing success
            if not is_pro:
                db.deduct_credit(user_id)
                print(f"💸 Credit deducted for user: {user_id}")
        else:
            print(f"❌ [Task {task_id}] Video utility processing failed.")
            batch_tasks[task_id] = {"status": "failed", "error": "Failed to split video parts safely."}
            
    except Exception as e:
        print(f"🚨 [Task {task_id}] Fatal crash in processing loop: {str(e)}")
        batch_tasks[task_id] = {"status": "failed", "error": str(e)}
        
    finally:
        # Clean up the massive input video block from disk storage
        try:
            if os.path.exists(input_video):
                os.remove(input_video)
        except Exception:
            pass


@app.post("/api/batch-split")
@limiter.limit("5/minute")
async def process_batch_split(
    request: Request,
    background_tasks: BackgroundTasks,  # 🌟 Injected FastAPI background worker queue
    video_file: UploadFile = File(...),
    clip_duration: int = Form(60),
    user_id: str = Form(...)
):
    user_data = db.get_or_create_user(user_id)

    if not user_data:
        print(f"🚨 Blocked: User {user_id} not found in Firebase!")
        raise HTTPException(status_code=401, detail="User profile not found. Please log in securely.")

    is_pro = user_data.get("isProUser", False)
    credits_left = user_data.get("free_credits", 0)

    if not is_pro and credits_left <= 0:
        print(f"🚨 Blocked: User {user_id} is out of credits!")
        raise HTTPException(status_code=402, detail="PaywallTrigger: Daily limit reached. Upgrade to Pro.")
    
    input_video = f"downloads/temp_batch_{video_file.filename}"
    
    # Save video streaming byte buffers to storage disk
    with open(input_video, "wb") as buffer:
        buffer.write(await video_file.read())

    # Generate a unique task identification hash for the frontend tracking system
    task_id = str(uuid.uuid4())
    batch_tasks[task_id] = {"status": "processing", "file_name": None}
    
    print(f"⚡ Instant Handoff: Task {task_id} generated. Routing long render loop to background worker queue.")
    
    # 🔥 Push task to the background processing layer and instantly release the HTTP response path
    background_tasks.add_task(
        background_split_task, 
        input_video, 
        clip_duration, 
        user_id, 
        is_pro, 
        task_id
    )
        
    return {
        "message": "Accepted", 
        "status": "processing", 
        "task_id": task_id
    }


@app.get("/api/batch-status/{task_id}")
async def check_batch_status(task_id: str):
    """ Simple polling tracker endpoint so your frontend can monitor progress safely """
    task = batch_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Requested background batch processing task not found.")
    return task
@app.get("/test-db")
def test_database():
    user_data = db.get_or_create_user("ceo@vaniconnect.com")
    return {"message": "Database is working perfectly!", "user_data": user_data}

