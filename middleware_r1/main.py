from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import requests
import os

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def home():
    return "<html><body><h1>Rabbit R1 Middleware Running</h1></body></html>"

# Retrieval Plugin API URL (Modify if needed)
RETRIEVAL_PLUGIN_URL = os.getenv("RETRIEVAL_PLUGIN_URL", "https://your-app-url.com")
API_KEY = os.getenv("RETRIEVAL_PLUGIN_API_KEY", "your-api-key")

@app.get("/", response_class=HTMLResponse)
def home_page():
    """
    Simple HTML interface for Rabbit R1 to interact with the retrieval plugin.
    """
    return """
    <html>
    <head><title>Rabbit R1 Memory Interface</title></head>
    <body>
        <h1>Rabbit R1 Memory Interface</h1>
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

@app.post("/save", response_class=HTMLResponse)
def save_memory(text: str):
    """
    Receives a text memo from Rabbit R1 and stores it in the retrieval database.
    """
    payload = {
        "documents": [
            {
                "id": "rabbit_r1_" + str(hash(text)),
                "text": text,
                "metadata": {"source": "rabbit_r1"}
            }
        ]
    }

    headers = {"Authorization": f"Bearer {API_KEY}"}
    response = requests.post(f"{RETRIEVAL_PLUGIN_URL}/upsert", json=payload, headers=headers)
    
    if response.status_code != 200:
        return f"Error: {response.text}"
    
    return "<html><body><h2>Memory saved successfully!</h2></body></html>"

@app.post("/get", response_class=HTMLResponse)
def get_memories(query: str):
    """
    Retrieves stored memos based on a user query.
    """
    payload = {"queries": [{"query": query}]}
    headers = {"Authorization": f"Bearer {API_KEY}"}
    response = requests.post(f"{RETRIEVAL_PLUGIN_URL}/query", json=payload, headers=headers)
    
    if response.status_code != 200:
        return f"Error: {response.text}"
    
    return f"<html><body><h2>Retrieved Memories:</h2><p>{response.json()}</p></body></html>"
