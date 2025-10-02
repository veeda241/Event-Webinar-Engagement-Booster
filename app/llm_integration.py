import os
import requests
from .models import User, Event

LLM_API_URL = os.getenv("LLM_API_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY")

def generate_personalized_content(user: User, event: Event, message_type: str) -> str:
    """
    Generates personalized content using an LLM.
    
    message_type can be: 'welcome', 'reminder_24h', 'reminder_1h', 'follow_up'
    """
    # The prompt is structured for an instruction-tuned model and includes a one-shot example for better formatting.
    prompt = f"""[INST] You are a friendly and professional event assistant. Your task is to generate the content for a '{message_type}' email based on the provided details.

### Example Output Format
Subject: Your Subject Here

Hi [User Name],

This is the body of the email.

Best,
The Event Team

### User Details
- Name: {user.name}
- Interests: {user.interests}

### Event Details
- Name: {event.name}
- Description: {event.description}
- Time: {event.event_time}

### Instructions
- For a 'welcome' message, be warm, confirm their registration, and mention how the event relates to their interests.
- For a 'reminder_24h' or 'reminder_1h' message, build excitement and provide a placeholder for the event link like [EVENT_LINK].
- For a 'follow_up' message, thank them for attending and provide the recording link: {event.recording_url}.
- The output must strictly follow the example format, starting with 'Subject:'.
[/INST]
"""

    print(f"🤖 Generating LLM content for {user.email} - Type: {message_type}")

    try:
        headers = {"Authorization": f"Bearer {LLM_API_KEY}"}
        payload = {
            "inputs": prompt,
            "parameters": {"max_new_tokens": 250} # Limit the length of the response
        }
        response = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=20)
        response.raise_for_status() # Raise an exception for bad status codes
        
        # Extract the generated text from the response
        generated_text = response.json()[0]['generated_text']
        # The response includes the prompt, so we strip it out.
        content = generated_text.replace(prompt, "").strip()
        return content

    except requests.exceptions.RequestException as e:
        print(f"❌ LLM API call failed: {e}")
        # Fallback to a simple template if the API call fails
        subject = f"Regarding {event.name}"
        body = f"Hi {user.name},\n\nThis is a {message_type} message for the event '{event.name}'.\n\nEvent Time: {event.event_time}\n\nBest,\nEvent Team"
        return f"Subject: {subject}\n\n{body}"