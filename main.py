# main.py
import os
import time
import requests
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()

import llm_handler
import github_handler

# Configuration
API_SECRET = os.getenv("API_SECRET")

app = FastAPI()

# Pydantic models for request validation
class Attachment(BaseModel):
    name: str
    url: str

class TaskRequest(BaseModel):
    email: str
    secret: str
    task: str
    round: int
    nonce: str
    brief: str
    checks: List[str]
    evaluation_url: str
    attachments: Optional[List[Attachment]] = None

class EvaluationPayload(BaseModel):
    email: str
    task: str
    round: int
    nonce: str
    repo_url: str
    commit_sha: str
    pages_url: str

def notify_evaluation_server(evaluation_url: str, payload: EvaluationPayload):
    """Notifies the evaluation server with exponential backoff."""
    delay = 1
    max_retries = 5
    for i in range(max_retries):
        try:
            print(f"Attempt {i+1}: Sending payload to {evaluation_url}")
            response = requests.post(evaluation_url, json=payload.dict())
            response.raise_for_status()
            print(f"Successfully notified evaluation server. Status: {response.status_code}")
            print(f"Response: {response.text}")
            return
        except requests.exceptions.RequestException as e:
            print(f"Error notifying evaluation server: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2
    print("Failed to notify evaluation server after multiple retries.")

def process_round_1_task(req: TaskRequest):
    """Handles the logic for a new build request (Round 1)."""
    print(f"Processing Round 1 for task: {req.task}")
    
    # 1. Generate code using the LLM
    generated_code = llm_handler.generate_code(req.brief, req.checks, req.attachments)
    
    # 2. Create repo and push code
    repo_url, commit_sha, pages_url = github_handler.create_and_push_repo(req.task, generated_code)
    
    print(f"Repo created: {repo_url} with commit {commit_sha}")
    print(f"Pages URL should be live shortly at: {pages_url}")

    # Wait for GitHub Pages to deploy
    print("Waiting 60 seconds for GitHub Pages to deploy...")
    time.sleep(60)
    
    # 3. Prepare and send payload to evaluation server
    payload = EvaluationPayload(
        email=req.email,
        task=req.task,
        round=req.round,
        nonce=req.nonce,
        repo_url=repo_url,
        commit_sha=commit_sha,
        pages_url=pages_url,
    )
    notify_evaluation_server(req.evaluation_url, payload)

def process_round_2_task(req: TaskRequest):
    """Handles the logic for a revision request (Round 2)."""
    print(f"Processing Round 2 for task: {req.task}")

    # 1. Get existing code from the GitHub repo
    existing_code = github_handler.get_existing_code(req.task)
    if not existing_code:
        raise HTTPException(status_code=500, detail="Could not retrieve existing code from repo.")

    # 2. Get updated code from the LLM
    updated_code = llm_handler.update_code(req.brief, req.checks, existing_code)

    # 3. Push the update to the repo
    commit_sha = github_handler.update_repo(req.task, updated_code)
    
    repo_url = f"https://github.com/{os.getenv('GITHUB_USER')}/{req.task}"
    pages_url = f"https://{os.getenv('GITHUB_USER')}.github.io/{req.task}/"

    print(f"Repo updated: {repo_url} with new commit {commit_sha}")
    print("Waiting 60 seconds for GitHub Pages to redeploy...")
    time.sleep(60)

    # 4. Prepare and send payload
    payload = EvaluationPayload(
        email=req.email,
        task=req.task,
        round=req.round,
        nonce=req.nonce,
        repo_url=repo_url,
        commit_sha=commit_sha,
        pages_url=pages_url,
    )
    notify_evaluation_server(req.evaluation_url, payload)

@app.post("/api/submit")
async def handle_task(req: TaskRequest, background_tasks: BackgroundTasks):
    """
    Main API endpoint to receive tasks.
    It verifies the secret and starts the processing in the background.
    """
    # 1. Verify the secret
    if req.secret != API_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret.")

    # 2. Add the correct task to the background queue
    if req.round == 1:
        background_tasks.add_task(process_round_1_task, req)
    elif req.round >= 2:
        background_tasks.add_task(process_round_2_task, req)
    else:
        raise HTTPException(status_code=400, detail="Invalid round number.")

    # 3. Return an immediate 200 OK response
    return {"status": "success", "message": "Task received and is being processed."}

@app.get("/")
def read_root():
    return {"message": "LLM Code Deployment API is running."}