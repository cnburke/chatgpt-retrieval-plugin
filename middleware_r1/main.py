from fastapi import FastAPI, HTTPException, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
import requests
import os

app = FastAPI()

# Initialize Rate Limiting (Disabled for Debugging)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(HTTPException, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Retrieval Plugin API URL (Modify if needed)
RETRIEVAL_PLUGIN_URL = os.getenv("RETRIEVAL_PLUGIN_URL", "https://your-app-url.com")
API_KEY = os.getenv("RETRIEVAL_PLUGIN_API_KEY", "your-api-key")

# Secure API key (Store this in an environment variable)
RABBIT_R1_API_KEY = os.getenv("RABBIT_R1_API_KEY", "hitpur-gyxsuS-0tadku")

# Simulated session storage for Rabbit R1 login
VALID_SESSIONS = {}

# Whitelist of allowed session IDs (Only known Rabbit R1 devices)
ALLOWED_SESSION_IDS = {"rabbit-user-123", "trusted-r1-device"}

@app.get("/", response_class=HTMLResponse)
def home_page(request: Request):
    """
    Simple HTML interface for Rabbit R1 to interact with the retrieval plugin.
    """
    session_cookie = request.cookies.get("session_id")
    logged_in = session_cookie in VALID_SESSIONS and VALID_SESSIONS[session_cookie]
    login_section = (
        "<p>Logged in as Rabbit R1</p><form action='/logout' method='post'><button type='submit'>Logout</button></form>"
        if logged_in
        else "<form action='/login' method='post'><label for='session_id'>Session ID:</label>"
             "<input type='text' id='session_id' name='session_id' required>"
             "<label for='api_key'>API Key:</label>"
             "<input type='password' id='api_key' name='api_key' required>"
             "<button type='submit'>Login</button></form>"
    )
    
    return f"""
    <html>
    <head><title>Rabbit R1 Memory Interface</title></head>
    <body>
        <h1>Rabbit R1 Memory Interface</h1>
        {login_section}
        <form action="/save" method="post">
            <label for="text">Enter Memory:</label>
            <input type="text" id="text" name="text" required>
            <button type="submit">Save</button>
        </form>
        <form action="/get" method="post">
            <label for="query">Retrieve Memory:</label>
            <input type="text" id="query" name="query" required>
            <button type="submit">Retrieve</button>
        </form>
    </body>
    </html>
    """

@app.post("/login")
def login(request: Request, session_id: str = Form(...), api_key: str = Form(...)):
    """
    Handles login by setting a session cookie.
    """
    response = HTMLResponse("<html><body><h2>Login Successful!</h2></body></html>")  # ✅ New: Display confirmation page instead of redirecting
    
    if api_key != RABBIT_R1_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    if session_id not in ALLOWED_SESSION_IDS:
        raise HTTPException(status_code=403, detail="Unauthorized Session ID")

    VALID_SESSIONS[session_id] = True

    # ✅ Ensure the cookie is set and visible to Rabbit R1
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=False,  # ✅ Change to False for testing
        secure=True,  # Ensures it's sent over HTTPS
        samesite="Lax",  # Allows cross-site requests within limits
        max_age=3600  # Expires in 1 hour
    )

    return response  # ✅ No redirect, so Rabbit R1 has time to store the cookie

@app.post("/logout")
def logout(request: Request, response: Response):
    """
    Logs out the user by clearing the session cookie.
    """
    session_cookie = request.cookies.get("session_id")
    if session_cookie and session_cookie in VALID_SESSIONS:
        del VALID_SESSIONS[session_cookie]
    response.delete_cookie("session_id")
    return RedirectResponse(url="/", status_code=303)

@app.post("/save", response_class=HTMLResponse)
def save_memory(request: Request, text: str = Form(...)):
    """
    Receives a text memo from Rabbit R1 and stores it in the retrieval database.
    """
    session_cookie = request.cookies.get("session_id")
    if not session_cookie or session_cookie not in VALID_SESSIONS or not VALID_SESSIONS[session_cookie]:
        return RedirectResponse(url="/", status_code=303)
    
    # ✅ Ensure a valid `source` value (Default to "chat")
    valid_sources = {"email", "file", "chat"}
    source_value = "chat"  # Default to "chat" if not provided or invalid

    payload = {
        "documents": [
            {
                "id": "rabbit_r1_" + str(hash(text)),
                "text": text,
                "metadata": {
                    "source": source_value,  # ✅ Ensured valid source
                    "source_id": "rabbit_r1",
                    "url": "",
                    "created_at": "2025-02-16T00:00:00Z",
                    "author": "Rabbit R1",
                    "document_id": "rabbit_r1_memory"
                }
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(f"{RETRIEVAL_PLUGIN_URL}/upsert", json=payload, headers=headers)

    if response.status_code != 200:
        return f"Error: {response.text}"
    
    return "<html><body><h2>Memory saved successfully!</h2></body></html>"

@app.post("/get", response_class=HTMLResponse)
def get_memories(request: Request, query: str = Form(...)):
    """
    Retrieves stored memos based on a user query.
    """
    session_cookie = request.cookies.get("session_id")
    if not session_cookie or session_cookie not in VALID_SESSIONS or not VALID_SESSIONS[session_cookie]:
        return RedirectResponse(url="/", status_code=303)
    
    payload = {"queries": [{"query": query}]}
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    response = requests.post(f"{RETRIEVAL_PLUGIN_URL}/query", json=payload, headers=headers)
    
    if response.status_code != 200:
        return f"Error: {response.text}"
    
    return f"<html><body><h2>Retrieved Memories:</h2><p>{response.json()}</p></body></html>"
