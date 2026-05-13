import streamlit as st
import os
from dotenv import load_dotenv
from agents import searcher_agent, reader_agent, writer_agent, critic_agent

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
    default_gemini = os.getenv("GEMINI_API_KEY", "")
    
    tavily_api_key = st.text_input("Tavily API Key", value=default_tavily, type="password")
    gemini_api_key = st.text_input("Gemini API Key", value=default_gemini, type="password")
    
    st.markdown("---")
    st.markdown("### Agents Pipeline")
    st.markdown("1. **Searcher Agent**: Finds top 5 relevant links.")
    st.markdown("2. **Reader Agent**: Scrapes and reads content.")
    st.markdown("3. **Writer Agent**: Writes a valuable blog post.")
    st.markdown("4. **Critic Agent**: Reviews and critiques the post.")

topic = st.text_input("Enter the topic you want to research:")
start_btn = st.button("Start Research 🚀")

if start_btn:
    if not tavily_api_key or not gemini_api_key:
        st.error("Please provide both Tavily and Gemini API keys in the sidebar.")
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
                
            # Agent 3: Writer
            with st.status("Agent 3: Writing the blog post...", expanded=True) as status3:
                st.write("Drafting a comprehensive blog post based on the context...")
                blog_post = writer_agent(topic, search_results, detailed_context, gemini_api_key)
                st.write("Blog post written.")
                status3.update(label="Agent 3: Writing Complete!", state="complete", expanded=False)
                
            # Agent 4: Critic
            with st.status("Agent 4: Critiquing the blog post...", expanded=True) as status4:
                st.write("Reviewing the drafted blog post...")
                critique_report = critic_agent(topic, blog_post, gemini_api_key)
                st.write("Critique generated.")
                status4.update(label="Agent 4: Critique Complete!", state="complete", expanded=False)
                
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
