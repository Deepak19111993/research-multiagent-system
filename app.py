import streamlit as st
import os
from dotenv import load_dotenv
from agents import searcher_agent, reader_agent, writer_agent, critic_agent, parse_score

# Load environment variables from .env file if it exists
load_dotenv()

st.set_page_config(page_title="Multi-Agent Research System", page_icon="🕵️", layout="wide")

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
                    st.success(f"Target score reached ({score}/{target_score})!")
                    break
                else:
                    if attempt < max_iterations:
                        st.warning(f"Score {score} is below target {target_score}. Refining draft...")
                    else:
                        st.warning(f"Max iterations reached. Proceeding with the final draft (Score: {score}).")
                
                attempt += 1
                
            # Display Final Outputs
            st.success("Pipeline executed successfully! 🎉")
            
            st.markdown("---")
            st.header("📝 Final Blog Post")
            st.markdown(blog_post)
            
            st.markdown("---")
            st.header("🧐 Critic Report")
            st.markdown(critique_report)
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
