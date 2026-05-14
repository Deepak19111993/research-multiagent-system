import streamlit as st
import os
from dotenv import load_dotenv
from agents import searcher_agent, reader_agent, writer_agent, critic_agent, parse_score
from utils import create_markdown_file, create_html_file, create_pdf_file, create_word_file
from database import init_db, save_blog, get_user_blogs
import urllib.parse
import requests
import json

# Load environment variables from .env file if it exists
load_dotenv()

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

st.set_page_config(page_title="Multi-Agent Research System", page_icon="🕵️", layout="wide")

# Initialize DB
init_db()

# Custom Robust Google OAuth Flow
try:
    if 'google_oauth' in st.secrets:
        # Load from Streamlit Cloud Secrets
        creds = st.secrets['google_oauth']
    else:
        # Load from local file
        with open('google_credentials.json', 'r') as f:
            creds = json.load(f)['web']
        
    client_id = creds['client_id']
    client_secret = creds['client_secret']
    auth_uri = creds.get('auth_uri', 'https://accounts.google.com/o/oauth2/auth')
    token_uri = creds.get('token_uri', 'https://oauth2.googleapis.com/token')
    # Pulls the first redirect URI from your credentials file
    redirect_uri = creds.get('redirect_uris', ['http://localhost:8501'])[0]
    
    if not st.session_state.get('connected'):
        st.title("🕵️ Multi-Agent Research System")
        st.markdown("Please log in with your Google account to access the research agents and save your blogs.")
        
        if 'code' in st.query_params:
            # We got a code from Google, exchange it for a token
            code = st.query_params['code']
            data = {
                'code': code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code'
            }
            res = requests.post(token_uri, data=data)
            
            if res.status_code == 200:
                access_token = res.json().get('access_token')
                user_res = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers={'Authorization': f'Bearer {access_token}'})
                
                if user_res.status_code == 200:
                    st.session_state['connected'] = True
                    st.session_state['user_info'] = user_res.json()
                    st.query_params.clear()
                    st.rerun()
                else:
                    st.error("Failed to fetch user profile from Google.")
            else:
                st.error("Login failed. Check your credentials.")
                st.query_params.clear()
        else:
            # Show login button
            scope = "https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile"
            auth_url = f"{auth_uri}?client_id={client_id}&redirect_uri={urllib.parse.quote(redirect_uri)}&response_type=code&scope={urllib.parse.quote(scope)}&access_type=online"
            st.markdown(f'<a href="{auth_url}" target="_self"><button style="background-color:#4285F4;color:white;padding:12px 20px;border-radius:5px;border:none;cursor:pointer;font-weight:bold;font-size:16px;">Login with Google</button></a>', unsafe_allow_html=True)
            
        st.stop() # Stop execution until logged in

except FileNotFoundError:
    st.error("google_credentials.json not found! Please create it.")
    st.stop()
except Exception as e:
    st.error(f"OAuth Setup Error: {str(e)}")
    st.stop()

# Initialize Session State
if 'current_view' not in st.session_state:
    st.session_state.current_view = None

user_info = st.session_state.get('user_info', {})
user_email = user_info.get('email', 'unknown@example.com')

st.sidebar.markdown(f"Logged in as **{user_info.get('name', 'User')}**")
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()
st.sidebar.markdown("---")

st.title("🕵️ Multi-Agent Research System")
st.markdown("This system uses 4 distinct agents to research, read, write, and critique a topic of your choice.")

# Sidebar for API Keys
with st.sidebar:
    st.header("Configuration")
    
    # Pre-fill from environment variables if available
    default_tavily = os.getenv("TAVILY_API_KEY", "")
    
    tavily_api_key = st.text_input("Tavily API Key", value=default_tavily, type="password")
    
    llm_provider = st.selectbox("LLM Provider", ["Anthropic", "Gemini", "OpenAI", "OpenRouter"])
    
    if llm_provider == "Anthropic":
        default_key = os.getenv("ANTHROPIC_API_KEY", "")
        default_model = "claude-3-5-sonnet-20241022"
    elif llm_provider == "Gemini":
        default_key = os.getenv("GEMINI_API_KEY", "")
        default_model = "gemini-2.5-flash"
    elif llm_provider == "OpenAI":
        default_key = os.getenv("OPENAI_API_KEY", "")
        default_model = "gpt-4o-mini"
    elif llm_provider == "OpenRouter":
        default_key = os.getenv("OPENROUTER_API_KEY", "")
        default_model = "anthropic/claude-3.5-sonnet"
        
    llm_api_key = st.text_input(f"{llm_provider} API Key", value=default_key, type="password")
    model_name = st.text_input("Model Name", value=default_model)
    
    st.markdown("---")
    st.markdown("### Agents Pipeline")
    st.markdown("1. **Searcher Agent**: Finds top 5 relevant links.")
    st.markdown("2. **Reader Agent**: Scrapes and reads content.")
    st.markdown("3. **Writer Agent**: Writes a valuable blog post.")
    st.markdown("4. **Critic Agent**: Reviews and critiques the post.")

    st.markdown("---")
    st.markdown("### 📚 Blog History")
    
    # Fetch from SQLite database instead of session state
    user_blogs = get_user_blogs(user_email)
    
    if not user_blogs:
        st.info("No blogs generated yet.")
    else:
        # Ensure safe current_view bounds
        if st.session_state.current_view is None or st.session_state.current_view >= len(user_blogs):
            st.session_state.current_view = len(user_blogs) - 1
            
        history_options = [f"{i+1}. {item['topic']}" for i, item in enumerate(user_blogs)]
        selected_history_str = st.selectbox(
            "View Past Generation", 
            options=history_options, 
            index=st.session_state.current_view
        )
        selected_idx = int(selected_history_str.split('.')[0]) - 1
        st.session_state.current_view = selected_idx
        
topic = st.text_input("Enter the topic you want to research:")
start_btn = st.button("Start Research 🚀")

if start_btn:
    if not tavily_api_key or not llm_api_key:
        st.error(f"Please provide both Tavily and {llm_provider} API keys in the sidebar.")
    elif not topic:
        st.warning("Please enter a topic.")
    else:
        try:
            # Agent 1: Searcher
            with st.status("Agent 1: Searching for information...", expanded=True) as status1:
                st.write(f"Searching Tavily for: '{topic}'")
                search_results = searcher_agent(topic, tavily_api_key)
                st.write(f"Found {len(search_results)} relevant sources.")
                for res in search_results:
                    st.markdown(f"- [{res['title']}]({res['url']})")
                status1.update(label="Agent 1: Search Complete!", state="complete", expanded=False)
                
            # Agent 2: Reader
            with st.status("Agent 2: Reading detailed content...", expanded=True) as status2:
                st.write("Scraping and extracting text from the identified sources...")
                detailed_context = reader_agent(search_results)
                st.write("Finished reading sources.")
                status2.update(label="Agent 2: Reading Complete!", state="complete", expanded=False)
                
            # Iterative Writing and Critiquing
            max_iterations = 3
            target_score = 8
            attempt = 1
            
            blog_post = ""
            critique_report = ""
            
            while attempt <= max_iterations:
                st.markdown(f"### Iteration {attempt}/{max_iterations}")
                
                # Agent 3: Writer
                with st.status(f"Agent 3: Writing the blog post (Attempt {attempt})...", expanded=True) as status3:
                    if attempt == 1:
                        st.write("Drafting a comprehensive blog post based on the context...")
                        blog_post = writer_agent(topic, search_results, detailed_context, llm_provider, llm_api_key, model_name)
                    else:
                        st.write("Refining the blog post based on the critique...")
                        blog_post = writer_agent(topic, search_results, detailed_context, llm_provider, llm_api_key, model_name, previous_draft=blog_post, critique=critique_report)
                        
                    st.write("Blog post written.")
                    status3.update(label=f"Agent 3: Writing Complete (Attempt {attempt})!", state="complete", expanded=False)
                    
                # Agent 4: Critic
                with st.status(f"Agent 4: Critiquing the blog post (Attempt {attempt})...", expanded=True) as status4:
                    st.write("Reviewing the drafted blog post...")
                    critique_report = critic_agent(topic, blog_post, llm_provider, llm_api_key, model_name)
                    score = parse_score(critique_report)
                    st.write(f"Critique generated. Score: {score}/10")
                    status4.update(label=f"Agent 4: Critique Complete! Score: {score}/10", state="complete", expanded=False)
                    
                if score >= target_score:
                    st.success(f"Target score reached ({score}/10)!")
                    break
                else:
                    if attempt < max_iterations:
                        st.warning(f"Score {score} is below target {target_score}. Refining draft...")
                    else:
                        st.warning(f"Max iterations reached. Proceeding with the final draft (Score: {score}).")
                
                attempt += 1
                
            # Generation successful, save to history
            st.success("Pipeline executed successfully! 🎉")
            
            # Save directly to persistent SQLite database
            save_blog(user_email, topic, blog_post, critique_report, score)
            
            # Re-fetch blogs to update the length
            updated_blogs = get_user_blogs(user_email)
            st.session_state.current_view = len(updated_blogs) - 1
            
            # Streamlit rerun to ensure the sidebar updates immediately
            st.rerun()
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

# Re-fetch blogs for display block
user_blogs = get_user_blogs(user_email)

# Always run this block, regardless of start_btn
if st.session_state.current_view is not None and st.session_state.current_view < len(user_blogs):
    active_data = user_blogs[st.session_state.current_view]
    
    st.markdown("---")
    st.header(f"📝 Final Blog Post: {active_data['topic']}")
    st.markdown(active_data['blog_post'])
    
    st.markdown("### 📥 Download Options")
    col1, col2, col3, col4 = st.columns(4)
    
    # Prepare files
    md_bytes = create_markdown_file(active_data['blog_post'])
    html_bytes = create_html_file(active_data['blog_post'])
    pdf_bytes = create_pdf_file(active_data['blog_post'])
    word_bytes = create_word_file(active_data['blog_post'])
    
    filename_base = active_data['topic'].lower().replace(" ", "_").replace("/", "_")
    
    # Add unique keys for buttons based on current view index to avoid duplicate key errors
    view_key = st.session_state.current_view
    
    with col1:
        st.download_button("Download Markdown", data=md_bytes, file_name=f"{filename_base}.md", mime="text/markdown", key=f"md_{view_key}")
    with col2:
        st.download_button("Download HTML", data=html_bytes, file_name=f"{filename_base}.html", mime="text/html", key=f"html_{view_key}")
    with col3:
        st.download_button("Download PDF", data=pdf_bytes, file_name=f"{filename_base}.pdf", mime="application/pdf", key=f"pdf_{view_key}")
    with col4:
        st.download_button("Download Word", data=word_bytes, file_name=f"{filename_base}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"word_{view_key}")
    
    st.markdown("---")
    st.header("🧐 Critic Report")
    st.markdown(active_data['critique_report'])
