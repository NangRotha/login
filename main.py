import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv

# ផ្ទុក .env
load_dotenv()

app = FastAPI()

# បន្ថែម SessionMiddleware (ចាំបាច់សម្រាប់ Google Login)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "your-fallback-secret-key"))

# បន្ថែម CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # អនុញ្ញាតឱ្យអ្នកណាក៏អាចចូលប្រើបានដែរ
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# កំណត់ Templates (កែដោយប្រើ os.path ដើម្បីកុំឱ្យមានបញ្ហា Path នៅលើ Render)
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# កំណត់ OAuth
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# ផ្ទុកអ្នកប្រើប្រាស់ក្នុងមេម៉ូរី
users_db = {}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """ទំព័រដើម"""
    user_id = request.session.get("user_id")
    user = users_db.get(user_id) if user_id else None
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/auth/login")
async def login(request: Request):
    """បញ្ជូនអ្នកប្រើប្រាស់ទៅ Google"""
    redirect_uri = os.getenv('REDIRECT_URI')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/callback")
async def auth_callback(request: Request):
    """Callback ក្រោយពី Google យល់ព្រម"""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if user_info:
            user_id = user_info['sub']
            users_db[user_id] = {
                'id': user_id,
                'email': user_info['email'],
                'name': user_info.get('name', 'User'),
                'picture': user_info.get('picture', '')
            }
            
            # រក្សាទុកក្នុង Session
            request.session['user_id'] = user_id
            return RedirectResponse(url="/")
            
    except Exception as e:
        print(f"Error: {e}")
        return RedirectResponse(url="/?error=authentication_failed")
    
    return RedirectResponse(url="/?error=authentication_failed")

@app.get("/auth/logout")
async def logout(request: Request):
    """ចេញពីគណនី"""
    request.session.pop('user_id', None)
    return RedirectResponse(url="/")

@app.get("/api/user")
async def get_user(request: Request):
    """API ដើម្បីទាញយកព័ត៌មានអ្នកប្រើប្រាស់បច្ចុប្បន្ន"""
    user_id = request.session.get("user_id")
    if user_id and user_id in users_db:
        return users_db[user_id]
    return {"error": "Not logged in"}
