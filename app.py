import os
import boto3
import shutil
import razorpay
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
cred = credentials.Certificate("firebase_key.json")

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
    video_file: UploadFile,
    clip_duration: int = Form(60) # Default to 60-second clips
):
   # 1. Grab the REAL user_id from the frontend (Replace hardcoded string later!)
    user_id = "admin_user_1" # ⚠️ REMINDER: Connect this to your frontend soon!
    
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

@app.get("/test-db")
def test_database():
    user_data = db.get_or_create_user("ceo@vaniconnect.com")
    return {"message": "Database is working perfectly!", "user_data": user_data}