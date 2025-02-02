from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from langchain_openai import ChatOpenAI
from models.suitability_rating import SuitabilityRating
from utils.get_model import get_model, available_models
from prompts.company_info_prompt import company_info_prompt
import concurrent.futures
from fastapi.responses import JSONResponse

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Specific origin for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class JobRequest(BaseModel):
    title: str
    description: str
    models: List[str] = available_models
    prompt: str = company_info_prompt

class SuitabilityResponse(BaseModel):
    model: str
    score: int
    reason: str

class ProposalResponse(BaseModel):
    model: str
    proposal: str

def analyze_with_model(model_name: str, prompt: str, job_title: str, job_description: str):
    model = get_model(model_name)
    suitability_agent = model.with_structured_output(SuitabilityRating)
    
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"Job Title: {job_title}\n\nJob Description: {job_description}"}
    ]
    
    result = suitability_agent.invoke(messages)
    return model_name, result

def generate_proposal_with_model(model_name: str, prompt: str, job_title: str, job_description: str):
    model = get_model(model_name)
    proposal_agent = model
    
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"Job Title: {job_title}\n\nJob Description: {job_description}"}
    ]
    
    result = proposal_agent.invoke(messages)
    return model_name, result

@app.get("/available-models")
async def available_models():
    return available_models

@app.post("/analyze-job", response_model=List[SuitabilityResponse], methods=["POST", "OPTIONS"])
async def analyze_job(job: JobRequest):
    if request.method == "OPTIONS":
        return JSONResponse(status_code=204, headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        })
    try:
        # Use ThreadPoolExecutor for parallel execution
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(analyze_with_model, model, job.prompt, job.title, job.description)
                for model in job.models
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Format the response
        return [
            SuitabilityResponse(model=model_name, score=int(result.suitability_score), reason=result.reason)
            for model_name, result in results
        ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-proposal", response_model=List[ProposalResponse], methods=["POST", "OPTIONS"])
async def generate_proposal(job: JobRequest):
    if request.method == "OPTIONS":
        return JSONResponse(status_code=204, headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        })
    try:
        # Use ThreadPoolExecutor for parallel execution
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(generate_proposal_with_model, model, job.prompt, job.title, job.description)
                for model in job.models
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Format the response
        return [
            ProposalResponse(model=model_name, proposal=result.content)
            for model_name, result in results
        ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.options("/{rest_of_path:path}")
async def preflight_handler():
    return {
        "status": "ok",
        "headers": {
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }
    }

@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    print(f"Incoming request: {request.method} {request.url}")
    print(f"Origin header: {request.headers.get('origin')}")
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:3000"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    print("Response headers:", response.headers)
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 