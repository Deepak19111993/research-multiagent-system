import requests
from bs4 import BeautifulSoup
from google import genai
import openai
import anthropic
import json
import re

def call_llm(provider: str, api_key: str, model_name: str, prompt: str) -> str:
    """Helper function to call different LLM providers."""
    if not api_key:
        raise ValueError(f"{provider} API key is missing.")
        
    if provider == "Gemini":
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name or 'gemini-2.5-flash',
            contents=prompt,
        )
        return response.text
        
    elif provider == "OpenAI":
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model_name or 'gpt-4o-mini',
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
        
    elif provider == "Anthropic":
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model_name or 'claude-3-5-sonnet-20241022',
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
        
    elif provider == "OpenRouter":
        client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        response = client.chat.completions.create(
            model=model_name or 'anthropic/claude-3.5-sonnet',
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
        
    else:
        raise ValueError(f"Unsupported provider: {provider}")

def parse_score(critique_report: str) -> int:
    """Extracts the integer score from the critique report."""
    # Try the standard Score: X/10 format
    match = re.search(r'Score:\s*(\d+)/10', critique_report, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
            
    # Fallback for raw <score> tag if it hallucinates
    match = re.search(r'<score>(\d+)</score>', critique_report, re.IGNORECASE)
    if match:
        return int(match.group(1))
        
    # Generic fallback
    match = re.search(r'(\d+)/10', critique_report)
    if match:
        return int(match.group(1))
        
    return 0

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
                
                # Try to extract the best image (og:image or twitter:image)
                og_image = soup.find('meta', property='og:image')
                tw_image = soup.find('meta', attrs={'name': 'twitter:image'})
                image_url = None
                if og_image and og_image.get('content'):
                    image_url = og_image['content']
                elif tw_image and tw_image.get('content'):
                    image_url = tw_image['content']
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.extract()
                    
                # Get text
                text = soup.get_text(separator=' ', strip=True)
                
                # Truncate text to avoid massive token counts per page (e.g., 5000 chars)
                text = text[:5000]
                
                detailed_context += f"\\n\\n--- Source: {url} ---\\n"
                if image_url:
                    detailed_context += f"Featured Image for this source: ![Image]({image_url})\\n\\n"
                detailed_context += f"{text}"
            else:
                detailed_context += f"\\n\\n--- Source: {url} ---\\n[Failed to retrieve content. Status: {response.status_code}]"
        except Exception as e:
            detailed_context += f"\\n\\n--- Source: {url} ---\\n[Error retrieving content: {str(e)}]"
            
    return detailed_context

def writer_agent(topic: str, search_context: list, detailed_context: str, provider: str, api_key: str, model_name: str, previous_draft: str = None, critique: str = None) -> str:
    """
    Agent 3: Uses the selected LLM to write a readable and valuable blog post based on the context.
    If previous_draft and critique are provided, it refines the draft based on the critique.
    """
    if previous_draft and critique:
        prompt = f"""
You are an expert technical blog writer. Your task is to improve and refine a blog post about the topic: "{topic}".

Here is the previous draft:
{previous_draft}

Here is the critique report from an expert editor:
{critique}

Please rewrite the blog post addressing all the feedback provided in the critique. Ensure the final output is comprehensive, highly readable, well-structured with headings, and uses Markdown formatting. If any relevant Featured Images were provided in the context, be sure to include the best one at the top of your blog post.
"""
    else:
        prompt = f"""
You are an expert technical blog writer. Your task is to write a comprehensive, readable, and valuable blog post about the following topic: "{topic}".

Here are some search snippets for context:
{json.dumps(search_context, indent=2)}

Here is detailed content extracted from the web:
{detailed_context}

Write a well-structured blog post with an engaging introduction, informative body paragraphs with headings, and a clear conclusion. Use Markdown formatting. Make it insightful and easy to read.
If the detailed context includes any "Featured Image" URLs in markdown format, please select the most relevant one and include it at the very top of your blog post!
"""
    return call_llm(provider, api_key, model_name, prompt)

def critic_agent(topic: str, blog_post: str, provider: str, api_key: str, model_name: str) -> str:
    """
    Agent 4: Uses the selected LLM to review the blog post and generate a critique report.
    """
    prompt = f"""
You are a strict and insightful editor and critic. You have been given a blog post about the topic: "{topic}".

Here is the blog post:
{blog_post}

Please provide a detailed critique report. Evaluate the following:
1. Accuracy and depth of information
2. Readability and flow
3. Structure and formatting
4. Overall value to the reader

Provide your report in Markdown format. Highlight strengths, suggest areas for improvement, and conclude with an **Overall Score out of 10**.

**CRITICAL REQUIREMENT:** You MUST output the final score exactly in this format at the very end of your response: Score: X/10 (where X is an integer between 1 and 10).
"""
    return call_llm(provider, api_key, model_name, prompt)
