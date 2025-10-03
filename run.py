import uvicorn
import os
from dotenv import load_dotenv
 
if __name__ == "__main__":
    # Get the project's root directory.
    project_root = os.path.dirname(os.path.abspath(__file__))

    # --- Create a dedicated directory for the model cache ---
    cache_dir = os.path.join(project_root, 'cache')
    os.makedirs(cache_dir, exist_ok=True)

    # Load environment variables from a .env file in the project root
    load_dotenv(dotenv_path=os.path.join(project_root, '.env'))
 
    # --- Set Environment Variables for Subprocesses ---
    # Set PYTHONPATH to ensure modules are found by Uvicorn's reloader.
    os.environ["PYTHONPATH"] = project_root
    # Set HF_HOME to control where Hugging Face models are cached.
    os.environ["HF_HOME"] = cache_dir
    os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

    # Point uvicorn to the 'app' object inside the 'app.main' module.
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)