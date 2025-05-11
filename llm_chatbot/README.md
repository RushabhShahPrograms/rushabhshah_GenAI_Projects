# 🤖 Gemini AI Chatbot

A conversational AI chatbot powered by Google Gemini (via `langchain-google-genai`) and built with Gradio UI. This project integrates LangChain’s conversational memory and prompt engineering to enable rich, context-aware dialogue. Ideal for building intelligent virtual assistants, educational tutors, or support bots.

---

## 🚀 Features

- 🔥 Google Gemini 2.0 Flash integration
- 🧠 Conversational memory with `langchain`
- 🪄 Prompt templating for enhanced dialogue control
- 🌐 Interactive frontend using Gradio with avatars
- ✅ Uses `uv` as the package manager for isolated, reproducible environments

---

## 📦 Installation (via `uv`)

> ⚠️ Ensure `uv` is installed first. If not:
```bash
pip install uv
```

### 🛠️ Setup Instructions

```bash
uv init llm_chatbot
uv add -r requirements.txt
uv sync
uv run main.py
```

---

## 🔐 Environment Variables

Create a `.env` file in the root directory with the following:

```
GOOGLE_API_KEY=your_google_genai_api_key
```

---

## 🧪 Local Development

To launch the chatbot UI locally:

```bash
uv run main.py
```

This will start a Gradio interface that can optionally be shared publicly.

---

## 📁 Project Structure

```
llm_chatbot/
├── main.py               # Main application logic
├── requirements.txt      # Python dependencies
├── .env                  # API key (not committed to Git)
└── README.md             # You're here
```
