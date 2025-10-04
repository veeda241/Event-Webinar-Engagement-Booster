import os
import sys
import subprocess
import importlib.util
import urllib.request
import venv

def run_command(command_list):
    """Runs a command as a list of arguments using subprocess."""
    print(f"--- Running: {' '.join(command_list)}")
    try:
        # Using a list of arguments with subprocess.run is the safest way
        # to avoid shell quoting issues on all platforms.
        subprocess.run(command_list, check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"--- ERROR: Command failed with exit code {e.returncode}")
        print(f"--- STDOUT: {e.stdout}")
        print(f"--- STDERR: {e.stderr}")
        sys.exit(1)

def main():
    """Sets up the project environment."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    venv_dir = os.path.join(project_root, 'venv')

    # 1. Create virtual environment if it doesn't exist
    if not os.path.exists(venv_dir):
        print(f"--- Creating virtual environment in: {venv_dir}")
        venv.create(venv_dir, with_pip=False, prompt="EngageSphere")
    
    # 2. Determine the absolute paths for the venv executables
    if sys.platform == "win32":
        python_exe = os.path.join(venv_dir, 'Scripts', 'python.exe')
    else:
        python_exe = os.path.join(venv_dir, 'bin', 'python')

    # Ensure the python executable exists before proceeding
    if not os.path.exists(python_exe):
        print(f"--- ERROR: Virtual environment python not found at {python_exe}")
        sys.exit(1)
        
    # 3. Self-correction: If not running inside the venv, re-launch with the venv's python.
    # This is the most robust way to ensure the script operates in the correct context.
    if sys.executable.lower() != python_exe.lower():
        print("--- Script is not running in the virtual environment. Re-launching...")
        # Re-run the script with the correct python interpreter
        result = subprocess.run([python_exe, __file__])
        # Exit the current script with the exit code of the child script
        sys.exit(result.returncode)

    # 4. Add venv's site-packages to the path to find pip after it's installed.
    if sys.platform == "win32":
        site_packages = os.path.join(venv_dir, 'Lib', 'site-packages')
    else:
        py_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join(venv_dir, 'lib', py_version, 'site-packages')
    sys.path.insert(0, site_packages)

    # 5. Check for pip and install it if missing, avoiding subprocess.
    try:
        import pip
        print("--- Pip is already installed.")
    except ImportError:
        print("--- Pip not found. Downloading get-pip.py to install it.")
        get_pip_path = os.path.join(project_root, "get-pip.py")
        try:
            urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", get_pip_path)
            # Run get-pip by importing it as a module to avoid creating a new process.
            spec = importlib.util.spec_from_file_location("get_pip", get_pip_path)
            get_pip = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(get_pip)
            # After running, pip should be importable
            import pip._internal.cli.main
        finally:
            if os.path.exists(get_pip_path):
                os.remove(get_pip_path)
    
    # 6. Use pip's internal API to install packages, avoiding subprocess.
    from pip._internal.cli.main import main as pip_main

    print("--- Upgrading pip using internal API...")
    pip_upgrade_result = pip_main(['install', '--upgrade', 'pip'])
    if pip_upgrade_result != 0:
        print(f"--- ERROR: Pip upgrade failed with exit code {pip_upgrade_result}")
        sys.exit(1)

    print("--- Installing dependencies from requirements.txt using internal API...")
    requirements_path = os.path.join(project_root, 'requirements.txt')
    install_result = pip_main(['install', '-r', requirements_path])
    if install_result != 0:
        print(f"--- ERROR: Dependency installation failed with exit code {install_result}")
        sys.exit(1)

    print("\n✅ --- Setup complete! ---")
    print("To activate the virtual environment, run:")
    if sys.platform == "win32":
        print(r".\venv\Scripts\Activate.ps1")
    else:
        print("source venv/bin/activate")

if __name__ == "__main__":
    main()