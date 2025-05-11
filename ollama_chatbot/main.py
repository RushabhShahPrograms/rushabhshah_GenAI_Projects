import os
import streamlit as st
from langchain.prompts import PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import OllamaLLM

# Set page configuration
st.set_page_config(
    page_title="LangChain Ollama Chatbot",
    page_icon="🤖",
    layout="wide",
)

# Custom CSS for a more beautiful interface
st.markdown("""
<style>
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.8rem;
        margin-bottom: 1rem;
        display: flex;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .chat-message.user {
        background-color: #e6f7ff;
        border-left: 5px solid #1890ff;
    }
    .chat-message.bot {
        background-color: #f6f6f6;
        border-left: 5px solid #722ed1;
    }
    .chat-message .avatar {
        width: 45px;
        height: 45px;
        border-radius: 50%;
        object-fit: cover;
        margin-right: 1rem;
    }
    .chat-message .message {
        flex-grow: 1;
    }
    .stButton button {
        background-color: #1890ff;
        color: white;
        border-radius: 0.5rem;
        padding: 0.5rem 1rem;
        border: none;
    }
    .stButton button:hover {
        background-color: #096dd9;
    }
    .sidebar .sidebar-content {
        background-color: #f6f6f6;
    }
    h1, h2, h3 {
        color: #444;
        font-family: 'Arial', sans-serif;
    }
    .main > div {
        padding: 2rem;
        border-radius: 1rem;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "chain" not in st.session_state:
        st.session_state.chain = None
        
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
        
    if "model_name" not in st.session_state:
        st.session_state.model_name = "gemma3:1b"

def initialize_chain(model_name, temperature=0.7, system_prompt=None):
    """Initialize the conversation chain with the selected model using the updated LangChain API"""
    # Default system prompt
    if system_prompt is None:
        system_prompt = """You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe.
Your answers should not include harmful, unethical, racist, sexist, toxic, dangerous, or illegal content.
Please ensure that your responses are socially unbiased and positive in nature.
If a question does not make any sense, or is not factually coherent, explain why instead of answering something incorrect.
If you don't know the answer to a question, please don't share false information."""
    
    # Create the prompt template with system message
    template = f"""
    {system_prompt}
    
    Current conversation:
    {{history}}
    Human: {{input}}
    AI Assistant:"""
    
    prompt = PromptTemplate(
        input_variables=["history", "input"], 
        template=template
    )
    
    # Initialize the language model
    try:
        llm = OllamaLLM(model=model_name, temperature=temperature)
        
        # Create a function to format conversation history
        def format_history(messages):
            return "\n".join([f"{'Human' if isinstance(msg, HumanMessage) else 'AI Assistant'}: {msg.content}" 
                             for msg in messages])
        
        # Create the chain with the updated LangChain API
        chain = (
            {"history": lambda x: format_history(x["history"]), "input": lambda x: x["input"]}
            | prompt
            | llm
            | StrOutputParser()
        )
        
        return chain
    except Exception as e:
        st.error(f"Error initializing model: {e}")
        return None

def display_messages():
    """Display the conversation messages"""
    for idx, message in enumerate(st.session_state.messages):
        if message["role"] == "user":
            with st.container():
                st.markdown(f"""
                <div class="chat-message user">
                    <div class="avatar">👨‍💻</div>
                    <div class="message">{message["content"]}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            with st.container():
                st.markdown(f"""
                <div class="chat-message bot">
                    <div class="avatar">🤖</div>
                    <div class="message">{message["content"]}</div>
                </div>
                """, unsafe_allow_html=True)

def main():
    # Initialize session state
    initialize_session_state()
    
    # App title and description
    st.title("🤖 LangChain Ollama Chatbot")
    st.markdown("Chat with your favorite local LLM models through Ollama")
    
    # Sidebar for configurations
    with st.sidebar:
        st.header("Model Configuration")
        
        # Model selection
        model_options = ["gemma3:1b"]
        selected_model = st.selectbox("Choose a model", model_options, index=0)
        
        # Temperature slider
        temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.7, step=0.1)
        
        # System prompt
        system_prompt = st.text_area(
            "System Prompt", 
            value="""You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe.
Your answers should not include harmful, unethical, racist, sexist, toxic, dangerous, or illegal content.
Please ensure that your responses are socially unbiased and positive in nature.
If a question does not make any sense, or is not factually coherent, explain why instead of answering something incorrect.
If you don't know the answer to a question, please don't share false information.""",
            height=200
        )
        
        # Initialize/reset button
        if st.button("Initialize/Reset Chat"):
            # Check if the selected model is different from the current one
            if selected_model != st.session_state.model_name:
                st.session_state.model_name = selected_model
                
            # Initialize the conversation chain
            st.session_state.chain = initialize_chain(
                model_name=selected_model,
                temperature=temperature,
                system_prompt=system_prompt
            )
            
            # Clear the conversation history
            st.session_state.messages = []
            st.session_state.chat_history = []
            st.success(f"Chat initialized with {selected_model} model")
            st.rerun()
    
    # Initialize the conversation chain if it doesn't exist
    if st.session_state.chain is None:
        st.session_state.chain = initialize_chain(
            model_name=st.session_state.model_name,
            temperature=temperature,
            system_prompt=system_prompt
        )
    
    # Display the conversation
    display_messages()
    
    # Chat input
    if "user_input" not in st.session_state:
        st.session_state.user_input = ""
    
    # Create a form for chat input
    with st.form(key="chat_form", clear_on_submit=True):
        user_input = st.text_input("Your message:", key="user_input_field", placeholder="Type your message here...")
        submit_button = st.form_submit_button("Send")
    
    # When the user submits a message
    if submit_button and user_input:
        # Add the user message to the session state
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Add to the langchain format history
        st.session_state.chat_history.append(HumanMessage(content=user_input))
        
        try:
            # Get response from the model using the updated LangChain API
            response = st.session_state.chain.invoke({
                "input": user_input,
                "history": st.session_state.chat_history
            })
            
            # Add the model response to the session state
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Add to the langchain format history
            st.session_state.chat_history.append(AIMessage(content=response))
            
            # Rerun to display the new messages
            st.rerun()
        except Exception as e:
            st.error(f"Error getting response: {e}")

if __name__ == "__main__":
    main()