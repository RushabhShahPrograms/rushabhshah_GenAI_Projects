import os
import gradio as gr
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure API key
try:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        raise ValueError("Missing GOOGLE_API_KEY environment variable")
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    logger.error(f"API Configuration Error: {e}")
    raise

class GeminiChatbot:
    def __init__(self):
        self.conversation_history = []
        self.setup_model()
        
    def setup_model(self):
        try:
            # Template for our chat prompt
            template = """
            You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe.
            Your answers should be informative, engaging, and accurate. If a question doesn't make any sense, or isn't factually coherent, explain why instead of answering something not correct.
            If you don't know the answer to a question, please don't share false information.
            
            Current conversation:
            {history}
            Human: {input}
            AI Assistant:
            """
            
            prompt = PromptTemplate(
                input_variables=["history", "input"], 
                template=template
            )
            
            # Set up memory for conversation history
            memory = ConversationBufferMemory(return_messages=True)
            
            # Initialize the Gemini model
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                temperature=0.7,
                top_p=0.95,
                google_api_key=GOOGLE_API_KEY,
                convert_system_message_to_human=True
            )
            
            # Create conversation chain
            self.conversation = ConversationChain(
                llm=llm,
                memory=memory,
                prompt=prompt,
                verbose=False
            )
            
            logger.info("Gemini model successfully initialized")
            
        except Exception as e:
            logger.error(f"Model Setup Error: {e}")
            raise
    
    def get_response(self, user_message, history):
        try:
            if not user_message.strip():
                return "Please enter a message to continue the conversation."
            
            # Get response from the model
            response = self.conversation.predict(input=user_message)
            
            # Update history
            history.append((user_message, response))
            
            return response
        except Exception as e:
            logger.error(f"Response Generation Error: {e}")
            return f"I'm having trouble processing your request. Please try again later. (Error: {type(e).__name__})"

# Initialize the chatbot
chatbot = GeminiChatbot()

# Create Gradio interface
def launch_interface():
    with gr.Blocks(theme=gr.themes.Soft(primary_hue="blue")) as demo:
        gr.Markdown("""
        # 🤖 Gemini AI Chatbot
        Have a conversation with Google's Gemini model powered by LangChain! Ask questions, seek advice, or just chat.
        """)
        
        chatbot_ui = gr.Chatbot(
            label="Conversation",
            height=600,
            bubble_full_width=False,
            avatar_images=(
                "https://api.dicebear.com/7.x/thumbs/svg?seed=user",
                "https://api.dicebear.com/7.x/thumbs/svg?seed=assistant"
            )
        )
        
        with gr.Row():
            msg = gr.Textbox(
                show_label=False,
                placeholder="Type your message here...",
                container=False,
                scale=9
            )
            submit = gr.Button("Send", variant="primary", scale=1)
        
        clear = gr.Button("Clear Conversation")
        
        # Event handlers
        history = []
        
        def respond(message, chat_history):
            bot_response = chatbot.get_response(message, history)
            chat_history.append((message, bot_response))
            return "", chat_history
        
        def clear_conversation():
            chatbot.conversation_history = []
            return [], []
        
        # Set up event listeners
        submit.click(respond, [msg, chatbot_ui], [msg, chatbot_ui])
        msg.submit(respond, [msg, chatbot_ui], [msg, chatbot_ui])
        clear.click(clear_conversation, None, [chatbot_ui, msg])
        
        gr.Markdown("""
        ### 💡 Tips
        - Be specific in your questions for better answers
        - You can ask follow-up questions to dive deeper into a topic
        - Type 'help' if you need assistance with using this chatbot
        """)
        
    return demo

if __name__ == "__main__":
    try:
        demo = launch_interface()
        demo.launch(share=True)
    except Exception as e:
        logger.critical(f"Application Error: {e}")