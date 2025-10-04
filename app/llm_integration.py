
from fastapi.concurrency import run_in_threadpool
from transformers import pipeline, AutoTokenizer
from tqdm.auto import tqdm
from .models import User, Event
from .config import settings

def create_llm_pipeline():
    """
    Initializes and returns the text-generation pipeline.
    This function is called once at application startup.
    """
    model_name = settings.LLM_MODEL_NAME
    print(f"🤖 Initializing local LLM pipeline with model: {model_name}...")
    print("---")
    print("--- NOTE: The first time you run this, the model will be downloaded from Hugging Face.")
    print(f"--- The '{model_name}' model can be over 1GB, so this may take several minutes.")
    print("--- The application may appear to be 'hanging' during the download, please be patient.")
    print("---")
    try:
        # Initialize the pipeline. This will download the model on first run.
        # For models requiring authentication, ensure you are logged in via `huggingface-cli login`.
        # Using a custom progress bar with tqdm for better user feedback during download.
        with tqdm(total=1, desc="Downloading LLM (if not cached)", unit="model") as pbar:
            generator = pipeline("text-generation", model=model_name, trust_remote_code=True)
            pbar.update(1)

        generator = pipeline("text-generation", model=model_name, trust_remote_code=True)
        print(f"✅ LLM Pipeline initialized successfully.")
        return generator
    except Exception as e:
        print(f"❌ Failed to initialize LLM pipeline: {e}")
        return None

async def generate_personalized_content(generator: pipeline, user: User, event: Event, message_type: str) -> str:
    """
    Generates personalized content using an LLM.

    message_type can be: 'welcome', 'content_preview', 'reminder_24h', 'reminder_1h', 'event_starting', 'follow_up'
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
- For an 'event_starting' message, be energetic and concise. Announce that the event is starting now and provide the event link placeholder [EVENT_LINK].
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
    Analyzes the user's query to determine intent and generate a response.
    - If the intent is to perform an action (register, cancel), it returns a JSON string with the action and entities.
    - If the intent is a general question, it returns a natural language response.
    """
    # This new prompt is much more advanced. It asks the LLM to act as a function-calling agent.
    # It must determine if the user wants to chat or perform an action, and then return a specific JSON format.
    
    # Truncate context to avoid exceeding model's max sequence length
    max_context_length = 3000 # Characters, a safe approximation
    if len(context) > max_context_length:
        context = context[:max_context_length] + "\n... (context truncated)"

    prompt = f"""<|system|>You are the AI assistant for "EngageSphere". Your primary role is to help users by either answering their questions or performing actions for them. Analyze the user's query and the provided context, then choose one of the following two paths:

1.  **Function Call**: If the user's intent is to perform an action like registering for an event, canceling a registration, or listing their events, you MUST return a JSON object with the key `"action"` and other relevant parameters.
    - The possible actions are: `"register"`, `"cancel"`, `"list_registrations"`.
    - For `"register"` and `"cancel"`, you MUST also include an `"event_name"` key with the name of the event extracted from the query.
    - **Example 1 (Register)**: User asks "Can you sign me up for the AI conference?", you return `{{"action": "register", "event_name": "AI Conference"}}`
    - **Example 2 (Cancel)**: User asks "I can't make it to the Data Summit, please cancel it.", you return `{{"action": "cancel", "event_name": "Data Summit"}}`
    - **Example 3 (List)**: User asks "What am I registered for?", you return `{{"action": "list_registrations"}}`

2.  **Conversational Response**: If the user's query is a general question, a greeting, or anything that doesn't map to a function call, you MUST return a JSON object with a single key `"response"` containing your friendly, conversational answer. Base your answer ONLY on the provided "Project Context". If the answer isn't in the context, say you don't have that information.
    - **Example**: User asks "What is EngageSphere?", you return `{{"response": "EngageSphere is an AI-powered agent designed to boost engagement for webinars and events."}}`

You must only return a single, valid JSON object and nothing else.

</s>
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
            
        outputs = await run_in_threadpool(generator, prompt, max_new_tokens=150, do_sample=False) # Use do_sample=False for more predictable JSON
        generated_text = outputs[0]['generated_text']
        
        # Extract the JSON part of the response
        json_response = generated_text.split("<|assistant|>")[1].strip()

        # It's crucial to validate that the output is valid JSON before returning it.
        # The endpoint will handle the logic of parsing it.
        try:
            # Test if it's valid JSON
            import json
            json.loads(json_response)
            return json_response
        except json.JSONDecodeError:
            print(f"❌ Chatbot LLM returned invalid JSON: {json_response}")
            # Fallback to a simple response if the LLM fails to produce valid JSON
            return '{{"response": "I\'m sorry, I had a little trouble understanding that. Could you please rephrase?"}}'

    except Exception as e:
        print(f"❌ Chatbot LLM generation failed: {e}")
        return '{{"response": "I\'m sorry, but I\'m having trouble connecting to my brain right now. Please try again in a moment."}}'