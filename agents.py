import requests
from bs4 import BeautifulSoup
from google import genai
import json

def searcher_agent(topic: str, tavily_api_key: str) -> list:
    """
    Agent 1: Searches the topic using Tavily API and returns the top 5 URLs, titles, and snippets.
    """
    if not tavily_api_key:
        raise ValueError("Tavily API key is missing.")
        
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": tavily_api_key,
        "query": topic,
        "search_depth": "basic",
        "include_answer": False,
        "include_images": False,
        "include_raw_content": False,
        "max_results": 5,
    }
    
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        raise Exception(f"Tavily API request failed: {response.text}")
        
    data = response.json()
    results = data.get("results", [])
    
    # Extract just what we need
    extracted_results = []
    for r in results:
        extracted_results.append({
            "url": r.get("url"),
            "title": r.get("title"),
            "content": r.get("content") # this is the snippet
        })
        
    return extracted_results

def reader_agent(search_results: list) -> str:
    """
    Agent 2: Reads the URLs in detail and extracts their main text content.
    Returns a combined string of the detailed context.
    """
    detailed_context = ""
    
    for result in search_results:
        url = result.get("url")
        if not url:
            continue
            
        try:
            # We use a user-agent to avoid basic blocks
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.extract()
                    
                # Get text
                text = soup.get_text(separator=' ', strip=True)
                
                # Truncate text to avoid massive token counts per page (e.g., 5000 chars)
                text = text[:5000]
                
                detailed_context += f"\\n\\n--- Source: {url} ---\\n{text}"
            else:
                detailed_context += f"\\n\\n--- Source: {url} ---\\n[Failed to retrieve content. Status: {response.status_code}]"
        except Exception as e:
            detailed_context += f"\\n\\n--- Source: {url} ---\\n[Error retrieving content: {str(e)}]"
            
    return detailed_context

def writer_agent(topic: str, search_context: list, detailed_context: str, gemini_api_key: str) -> str:
    """
    Agent 3: Uses Gemini to write a readable and valuable blog post based on the context.
    """
    if not gemini_api_key:
        raise ValueError("Gemini API key is missing.")
        
    client = genai.Client(api_key=gemini_api_key)
    
    prompt = f"""
You are an expert technical blog writer. Your task is to write a comprehensive, readable, and valuable blog post about the following topic: "{topic}".

Here are some search snippets for context:
{json.dumps(search_context, indent=2)}

Here is detailed content extracted from the web:
{detailed_context}

Write a well-structured blog post with an engaging introduction, informative body paragraphs with headings, and a clear conclusion. Use Markdown formatting. Make it insightful and easy to read.
"""

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    
    return response.text

def critic_agent(topic: str, blog_post: str, gemini_api_key: str) -> str:
    """
    Agent 4: Uses Gemini to review the blog post and generate a critique report.
    """
    if not gemini_api_key:
        raise ValueError("Gemini API key is missing.")
        
    client = genai.Client(api_key=gemini_api_key)
    
    prompt = f"""
You are a strict and insightful editor and critic. You have been given a blog post about the topic: "{topic}".

Here is the blog post:
{blog_post}

Please provide a detailed critique report. Evaluate the following:
1. Accuracy and depth of information
2. Readability and flow
3. Structure and formatting
4. Overall value to the reader

Provide your report in Markdown format. Highlight strengths, suggest areas for improvement, and conclude with an **Overall Score out of 10** (e.g., "Overall Score: 8/10").
"""

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    
    return response.text
