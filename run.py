import uvicorn
import os
 
if __name__ == "__main__":
    # Get the project's root directory.
    project_root = os.path.dirname(os.path.abspath(__file__))
 
    # Set the PYTHONPATH environment variable. This is a robust way to ensure
    # that subprocesses (like the one Uvicorn's reloader creates)
    # know where to find your project's modules.
    os.environ["PYTHONPATH"] = project_root

    # Point uvicorn to the 'app' object inside the 'app.main' module.
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)