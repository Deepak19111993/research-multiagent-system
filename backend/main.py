import os
import json
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from dotenv import load_dotenv

from agents import searcher_agent, reader_agent, writer_agent, critic_agent, parse_score
from utils import create_markdown_file, create_html_file, create_pdf_file, create_word_file
from database import init_db, save_blog, get_user_blogs

load_dotenv()

app = FastAPI(title="Multi-Agent Research API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/")
def read_root():
    return {
        "status": "Online",
        "message": "Multi-Agent Research API is running successfully.",
        "endpoints": {
            "research": "/api/research (POST)",
            "history": "/api/history (GET)",
            "download": "/api/download (POST)"
        }
    }

class ResearchRequest(BaseModel):
    user_email: str
    topic: str
    tavily_api_key: str
    llm_provider: str
    llm_api_key: str
    model_name: str

@app.get("/api/history")
def get_history(user_email: str):
    blogs = get_user_blogs(user_email)
    return {"blogs": blogs}

@app.post("/api/research")
async def run_research_pipeline(req: ResearchRequest):
    # This endpoint streams the response using SSE
    async def event_generator():
        try:
            # Yield initial status
            yield f"data: {json.dumps({'status': 'Searching Tavily...', 'progress': 10})}\n\n"
            
            # Agent 1
            search_results = await asyncio.to_thread(searcher_agent, req.topic, req.tavily_api_key)
            yield f"data: {json.dumps({'status': f'Found {len(search_results)} sources. Reading content...', 'progress': 30})}\n\n"
            
            # Agent 2
            detailed_context = await asyncio.to_thread(reader_agent, search_results)
            yield f"data: {json.dumps({'status': 'Finished reading. Drafting blog post...', 'progress': 50})}\n\n"
            
            max_iterations = 3
            target_score = 8
            attempt = 1
            
            blog_post = ""
            critique_report = ""
            score = 0
            
            while attempt <= max_iterations:
                yield f"data: {json.dumps({'status': f'Writing draft (Attempt {attempt})...', 'progress': 50 + attempt*10})}\n\n"
                
                if attempt == 1:
                    blog_post = await asyncio.to_thread(writer_agent, req.topic, search_results, detailed_context, req.llm_provider, req.llm_api_key, req.model_name)
                else:
                    blog_post = await asyncio.to_thread(writer_agent, req.topic, search_results, detailed_context, req.llm_provider, req.llm_api_key, req.model_name, previous_draft=blog_post, critique=critique_report)
                
                yield f"data: {json.dumps({'status': f'Critiquing draft (Attempt {attempt})...', 'progress': 55 + attempt*10})}\n\n"
                
                critique_report = await asyncio.to_thread(critic_agent, req.topic, blog_post, req.llm_provider, req.llm_api_key, req.model_name)
                score = parse_score(critique_report)
                
                if score >= target_score:
                    break
                    
                attempt += 1
                
            yield f"data: {json.dumps({'status': f'Pipeline completed. Final Score: {score}/10', 'progress': 95})}\n\n"
            
            # Save to DB
            await asyncio.to_thread(save_blog, req.user_email, req.topic, blog_post, critique_report, score)
            
            # Yield final payload
            yield f"data: {json.dumps({'status': 'Complete', 'progress': 100, 'done': True, 'blog_post': blog_post, 'critique_report': critique_report, 'score': score})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

class DownloadRequest(BaseModel):
    content: str
    format: str
    topic: str

@app.post("/api/download")
def download_file(req: DownloadRequest):
    content = req.content
    format = req.format
    topic = req.topic.lower().replace(" ", "_").replace("/", "_")
    
    if format == "md":
        data = create_markdown_file(content)
        return Response(content=data, media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename={topic}.md"})
    elif format == "html":
        data = create_html_file(content)
        return Response(content=data, media_type="text/html", headers={"Content-Disposition": f"attachment; filename={topic}.html"})
    elif format == "pdf":
        data = create_pdf_file(content)
        return Response(content=data, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={topic}.pdf"})
    elif format == "word":
        data = create_word_file(content)
        return Response(content=data, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": f"attachment; filename={topic}.docx"})
    else:
        raise HTTPException(status_code=400, detail="Invalid format")
