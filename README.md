# Event-Webinar-Engagement-Booster

**EngageSphere** is an AI-powered intelligent agent designed to boost engagement for webinars and events. It tracks user registrations, analyzes their interests, and automates a personalized communication workflow. It sends everything from welcome messages and content previews to event reminders and post-event follow-ups, using email (via SendGrid) and chat (via WhatsApp/Twilio).

The core of the agent is a local LLM (powered by Hugging Face `transformers`) that generates unique, context-aware content for each user, ensuring that every communication feels personal and relevant.

## ✨ Features

- **User & Event Management**: Simple endpoints to create users and events.
- **Automated Registration Workflow**: Register users for events with a single API call.
- **Interest Analysis**: Automatically extracts keywords from event details to build and refine user interest profiles.
- **AI-Powered Event Importer**: Scrapes a URL and uses an LLM to automatically create an event, extracting its name, description, and date.
- **Personalized Content Generation**: Uses a local LLM to craft unique messages for different communication touchpoints (welcome, reminders, etc.).
- **Multi-Channel Messaging**:
    - **Email**: Integrated with SendGrid for robust and trackable email delivery.
    - **Chat**: Integrated with Twilio for sending WhatsApp messages.
- **Intelligent Scheduling**: Uses `APScheduler` to schedule all communications at the moment of registration (e.g., 24-hour reminder, 1-hour reminder, post-event follow-up).
- **Admin Features**: The first user created is automatically designated as an admin with privileges to create events.
- **AI Chatbot**: An integrated chatbot that can answer questions about the platform and its upcoming events, using the project's documentation as its knowledge base.

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, BeautifulSoup
- **Database**: SQLAlchemy (defaults to SQLite)
- **AI/ML**: Hugging Face `transformers` for local LLM inference
- **Scheduling**: `APScheduler`
- **Messaging**: SendGrid (Email), Twilio (WhatsApp)
- **Authentication**: JWT with Passlib for password hashing
- **Frontend**: Vanilla HTML, CSS, and JavaScript

## 🚀 Getting Started

### 1. Prerequisites
- MySQL Server
- Python 3.8+
- Hugging Face Account (if using a gated model)
- SendGrid Account (for sending emails)
- Twilio Account (for sending WhatsApp messages)

### 2. Clone the Repository

```bash
git clone <your-repo-url>
# The clone command creates a directory named 'Event-Webinar-Engagement-Booster'.
cd Event-Webinar-Engagement-Booster # Navigate into the newly created project folder.
```

### 3. Install Dependencies

Create a virtual environment and install the required packages from `requirements.txt`.

> **Note:** This project uses `lxml` for parsing, which may require system-level dependencies. If `pip install` fails, you may need to install `libxml2-dev` and `libxslt-dev` (on Debian/Ubuntu) or equivalent packages for your OS.

```sh
# Create a virtual environment (optional but recommended)
python -m venv venv
```

**Activate the virtual environment:**

*   **On Windows (PowerShell):**
    ```powershell
    .\venv\Scripts\Activate.ps1
    ```
    > **Note:** If you get an error about script execution being disabled, run this command first to allow scripts for the current session, then try activating again:
    > `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`

*   **On macOS / Linux:**
    ```bash
    source venv/bin/activate
    ```

**Deactivate the virtual environment:**

When you are finished working on the project, you can deactivate the virtual environment by simply running:

```bash
deactivate
```

### 4. Install Packages

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root and add the following variables.

```env
# --- Application Settings ---
DATABASE_URL="mysql+pymysql://user:password@localhost:3306/engage_sphere" # Example for MySQL
SECRET_KEY="a_very_strong_and_secret_key_for_jwt" # Replace with a real secret in production

# --- LLM Configuration ---
ENABLE_LOCAL_LLM="true" # Set to "false" to use simple templates instead of the LLM
LLM_MODEL_NAME="TinyLlama/TinyLlama-1.1B-Chat-v1.0" # Recommended small model

# For higher accuracy on tasks like data extraction, consider a more powerful model like:
# LLM_MODEL_NAME="mistralai/Mistral-7B-Instruct-v0.2"

# --- Messaging Services ---
SENDGRID_API_KEY="YOUR_SENDGRID_API_KEY"
SENDGRID_FROM_EMAIL="your-verified-sender@example.com"
TWILIO_ACCOUNT_SID="YOUR_TWILIO_ACCOUNT_SID"
TWILIO_AUTH_TOKEN="YOUR_TWILIO_AUTH_TOKEN"
TWILIO_WHATSAPP_FROM="whatsapp:+14155238886" # Your Twilio WhatsApp number
```

### 5. Run the Application

Start the FastAPI server using the provided `run.py` script.

```bash
python run.py
```

The application will be available at `http://127.0.0.1:8001`. The first account you create will automatically be granted admin privileges.
