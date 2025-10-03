import requests
from bs4 import BeautifulSoup
from fastapi.concurrency import run_in_threadpool
from transformers import pipeline
import json
from . import schemas, llm_integration

def _get_text_from_html(html_content: str) -> str:
    """
    Extracts clean, readable text from raw HTML content using BeautifulSoup.
    This helps provide a cleaner input for the LLM.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    # Remove script and style elements
    for script_or_style in soup(["script", "style", "nav", "footer", "header"]):
        script_or_style.decompose()
    # Get text and clean it up
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    return text

async def _extract_event_details_with_llm(generator: pipeline, text_content: str) -> schemas.EventCreate:
    """
    Uses the LLM to extract structured event data from unstructured text.
    It asks the LLM to return a JSON object, which we can then parse.
    """
    # This is a "few-shot" prompt. By providing a clear example, we guide the LLM
    # to produce a more accurate and correctly formatted JSON output.
    prompt = f"""<|system|>You are an expert data extraction assistant. Your task is to analyze the provided text from a webpage and extract the event details. You must return a single, valid JSON object with the keys "name", "description", and "event_time". The event_time must be in 'YYYY-MM-DD HH:MM:SS' format. If you cannot find a piece of information, use a null value for that key.</s>
<|user|>
### Example Input Text:
Join us for our annual developer conference, "CodeFusion 2024"! This year, we're exploring the future of AI in software development. The event kicks off on October 26th, 2024 at 9:00 AM PST. Don't miss out on insightful talks and hands-on workshops.

### Example JSON Output:
```json
{{
  "name": "CodeFusion 2024",
  "description": "An annual developer conference exploring the future of AI in software development, featuring insightful talks and hands-on workshops.",
  "event_time": "2024-10-26 09:00:00"
}}
```

### Webpage Text to Analyze:
{text_content[:4000]}

### Your JSON Output:
<|assistant|>
"""
    print("🤖 Using LLM to extract event details from URL content...")
    try:
        if generator is None:
            raise RuntimeError("LLM pipeline is not available.")

        outputs = await run_in_threadpool(generator, prompt, max_new_tokens=200, do_sample=False)
        generated_text = outputs[0]['generated_text']
        json_part = generated_text.split("<|assistant|>")[1].strip()

        # Clean up potential markdown formatting around the JSON
        if json_part.startswith("```json"):
            json_part = json_part[7:]
        if json_part.endswith("```"):
            json_part = json_part[:-3]

        data = json.loads(json_part)
        return schemas.EventCreate(**data)
    except Exception as e:
        print(f"❌ LLM extraction failed: {e}")
        raise ValueError("The AI failed to extract valid event details from the provided URL.")

async def import_event_from_url(url: str, llm_pipeline: pipeline) -> schemas.EventCreate:
    """Orchestrates the process of fetching a URL and extracting event data."""
    print(f"➡️ Starting import from URL: {url}")
    response = await run_in_threadpool(requests.get, url, headers={'User-Agent': 'Mozilla/5.0'})
    response.raise_for_status()
    clean_text = await run_in_threadpool(_get_text_from_html, response.text)
    event_data = await _extract_event_details_with_llm(llm_pipeline, clean_text)
    return event_data