
import os
from fastapi.concurrency import run_in_threadpool
from transformers import pipeline, AutoTokenizer
from .models import User, Event

def create_llm_pipeline():
    """
    Initializes and returns the text-generation pipeline.
    This function is called once at application startup.
    """
    model_name = os.getenv("LLM_MODEL_NAME", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
    print(f"🤖 Initializing local LLM pipeline with model: {model_name}...")
    try:
        # Initialize the pipeline. This will download the model on first run.
        # For models requiring authentication, ensure you are logged in via `huggingface-cli login`.
        # You can add device=0 to use a GPU if available: pipeline(..., device=0)
        generator = pipeline("text-generation", model=model_name, trust_remote_code=True)
        print(f"✅ LLM Pipeline initialized successfully.")
        return generator
    except Exception as e:
        print(f"❌ Failed to initialize LLM pipeline: {e}")
        return None

async def generate_personalized_content(generator: pipeline, user: User, event: Event, message_type: str) -> str:
    """
    Generates personalized content using an LLM.
    
    message_type can be: 'welcome', 'content_preview', 'reminder_24h', 'reminder_1h', 'follow_up'
    """
    # The prompt is structured for an instruction-tuned model and includes a one-shot example for better formatting.
    prompt = f"""<|system|>You are a friendly and professional event assistant. Your task is to generate the content for a '{message_type}' email based on the provided details. The output must strictly follow the example format, starting with 'Subject:'.</s>
<|user|>

### Example Output Format
Subject: Your Subject Here

Hi [User Name],

This is the body of the email.

Best,
The Event Team

### User Details
- Name: {user.name}
- Job Title: {user.job_title}
- Interests: {user.interests}

### Event Details
- Name: {event.name}
- Description: {event.description}
- Time: {event.event_time}

### Instructions
- For a 'welcome' message, be warm, confirm their registration, and mention how the event relates to their interests or job title.
- For a 'content_preview' message, generate excitement by giving a sneak peek of the event, like mentioning a key topic or a speaker's background.
- For a 'reminder_24h' or 'reminder_1h' message, build excitement and provide a placeholder for the event link like [EVENT_LINK].
- For a 'follow_up' message, thank them for attending and provide the recording link: {event.recording_url}.
<|assistant|>
"""

    print(f"🤖 Generating LLM content for {user.email} - Type: {message_type}")

    try:
        if generator is None:
            raise RuntimeError("LLM pipeline is not available.")
        
        # Run the blocking pipeline call in a separate thread
        outputs = await run_in_threadpool(generator, prompt, max_new_tokens=250, do_sample=True, temperature=0.7, top_k=50, top_p=0.95)
        generated_text = outputs[0]['generated_text']
        
        # The response includes the prompt, so we strip it out.
        return generated_text.split("<|assistant|>")[1].strip()
    except Exception as e:
        print(f"❌ LLM generation failed: {e}")
        # Fallback to a simple template if the API call fails
        subject = f"Regarding {event.name}"
        body = f"Hi {user.name},\n\nThis is a {message_type} message for the event '{event.name}'.\n\nEvent Time: {event.event_time}\n\nBest,\nEvent Team"
        return f"Subject: {subject}\n\n{body}"

async def generate_chatbot_response(generator: pipeline, query: str, context: str) -> str:
    """
    Generates a response for the chatbot based on a user query and project context.
    """
    prompt = f"""<|system|>You are a helpful assistant for the "EngageSphere" application. Your goal is to answer user questions based *only* on the provided context about the project. If the answer is not in the context, say that you don't have information on that topic. Be friendly and concise.</s>
<|user|>

### Project Context
{context}

### User Question
{query}
<|assistant|>
"""

    print(f"🤖 Generating chatbot response for query: '{query}'")

    try:
        if generator is None:
            raise RuntimeError("LLM pipeline is not available.")
            
        outputs = await run_in_threadpool(generator, prompt, max_new_tokens=150, do_sample=True, temperature=0.7, top_k=50, top_p=0.95)
        generated_text = outputs[0]['generated_text']
        return generated_text.split("<|assistant|>")[1].strip()
    except Exception as e:
        print(f"❌ Chatbot LLM generation failed: {e}")
        return "I'm sorry, but I'm having trouble connecting to my brain right now. Please try again in a moment."