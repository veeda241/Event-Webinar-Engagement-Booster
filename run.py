import uvicorn
import os
from dotenv import load_dotenv
 
if __name__ == "__main__":
    # Get the project's root directory.
    project_root = os.path.dirname(os.path.abspath(__file__))

    # Load environment variables from a .env file in the project root
    load_dotenv(dotenv_path=os.path.join(project_root, '.env'))
 
    # Set the PYTHONPATH environment variable. This is a robust way to ensure
    # that subprocesses (like the one Uvicorn's reloader creates)
    # know where to find your project's modules.
    os.environ["PYTHONPATH"] = project_root
    os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
    os.environ["ENABLE_LOCAL_LLM"] = "true"

    # Point uvicorn to the 'app' object inside the 'app.main' module.
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)