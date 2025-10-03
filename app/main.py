from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List
import os
from datetime import datetime, timedelta
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from . import models, schemas, services, database, security
from . import importer
from .scheduler import scheduler
from . import llm_integration

# Create database tables
models.Base.metadata.create_all(bind=database.engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    print("--- Application Startup ---")
    # Conditionally load the heavy LLM to allow for fast development reloads.
    if os.getenv("ENABLE_LOCAL_LLM", "false").lower() == "true":
        app.state.llm_pipeline = llm_integration.create_llm_pipeline()
    else:
        app.state.llm_pipeline = None
        print("⚠️  Local LLM is DISABLED. Using fallback templates. Set ENABLE_LOCAL_LLM=true to enable.")
    scheduler.start()
    print("🚀 Scheduler started.")
    yield
    # On shutdown
    print("--- Application Shutdown ---")
    scheduler.shutdown()
    print("Scheduler shut down.")

app = FastAPI(
    title="EngageSphere",
    description="An AI-powered agent to boost event engagement.",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware to allow the front-end to communicate with the backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(db: Session = Depends(database.get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate user and return a JWT access token.
    """
    user = security.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """
    Create a new user.
    """
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return security.create_user(db=db, user=user)

@app.post("/events/", response_model=schemas.Event)
def create_event(
    event: schemas.EventCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_admin_user)
):
    """
    Create a new event in the database.
    (Admin only)"""
    db_event = models.Event(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

@app.post("/import-event/", response_model=schemas.Event)
async def import_event_from_url(
    request: Request,
    import_request: schemas.ImportRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_admin_user)
):
    """
    Imports an event by scraping a URL and using an LLM to extract details.
    (Admin only)
    """
    llm_pipeline = request.app.state.llm_pipeline
    if llm_pipeline is None:
        raise HTTPException(status_code=400, detail="LLM is not enabled. Cannot import from URL.")
    try:
        event_data = await importer.import_event_from_url(import_request.url, llm_pipeline)
        db_event = models.Event(**event_data.model_dump())
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        return db_event
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to import from URL: {str(e)}")

@app.get("/events/", response_model=List[schemas.Event])
def read_events(db: Session = Depends(database.get_db)):
    """
    Retrieve all events from the database.
    """
    # Only return events that are in the future, sorted by the soonest first.
    events = db.query(models.Event)\
        .filter(models.Event.event_time >= datetime.utcnow())\
        .order_by(models.Event.event_time.asc()).all()
    return events

@app.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(security.get_current_user)):
    """
    Get the details of the currently authenticated user.
    """
    return current_user

@app.get("/users/me/registrations", response_model=List[int])
async def get_my_registrations(current_user: models.User = Depends(security.get_current_user), db: Session = Depends(database.get_db)):
    """
    Get a list of event IDs the current user is registered for.
    """
    registrations = db.query(models.Registration.event_id).filter(models.Registration.user_id == current_user.id).all()
    # The result is a list of tuples, so we extract the first element of each tuple.
    registered_event_ids = [reg[0] for reg in registrations]
    return registered_event_ids


@app.delete("/events/{event_id}", status_code=200)
def delete_event(
    event_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_admin_user)
):
    """
    Delete an event, all its registrations, and cancel all associated scheduled jobs.
    (Admin only)"""
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    # Find all registrations for this event to cancel their scheduled jobs
    registrations = db.query(models.Registration).filter(models.Registration.event_id == event_id).all()
    
    for reg in registrations:
        user_id = reg.user_id
        # Define the job IDs based on the convention set in services.py
        job_ids_to_remove = [
            f"preview_{user_id}_{event_id}",
            f"reminder_24h_{user_id}_{event_id}",
            f"reminder_1h_{user_id}_{event_id}",
            f"follow_up_{user_id}_{event_id}"
        ]
        for job_id in job_ids_to_remove:
            try:
                scheduler.remove_job(job_id)
                print(f"✅ Canceled scheduled job: {job_id}")
            except Exception as e:
                # This will happen if the job was already executed or never existed, which is fine.
                print(f"ⓘ Could not cancel job {job_id} (it may have already run): {e}")

    # Delete associated registrations first to maintain foreign key integrity
    db.query(models.Registration).filter(models.Registration.event_id == event_id).delete()

    # Now delete the event
    db.delete(db_event)
    db.commit()

    return {"message": f"Event with ID {event_id} and all its registrations have been deleted."}

@app.get("/events/{event_id}", response_model=schemas.Event)
def read_event(event_id: int, db: Session = Depends(database.get_db)):
    """Retrieve a single event by its ID."""
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return db_event


@app.post("/register/", response_model=schemas.RegistrationResponse)
async def register_for_event(
    request: Request,
    registration_request: schemas.EventRegistrationRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Register the currently authenticated user for an event.
    This endpoint is protected and requires a valid JWT token.
    """
    try:
        llm_pipeline = request.app.state.llm_pipeline
        # The user is now passed from the token dependency
        user, event = await services.process_registration(db, current_user, registration_request.event_id, llm_pipeline)
        services.schedule_all_communications(user.id, event.id, llm_pipeline)
        return {"message": "Registration successful and communications scheduled.", "user_email": user.email, "event_id": event.id}
    except ValueError as e: # Catching specific, known errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

# --- Chatbot Endpoint ---
@app.post("/chatbot/")
async def chat_with_bot(fastapi_req: Request, chat_req: schemas.ChatRequest, db: Session = Depends(database.get_db)):
    """
    Handles chatbot conversations.
    Uses the project's README as context for the LLM.
    """
    try:
        llm_pipeline = fastapi_req.app.state.llm_pipeline
        if llm_pipeline is None:
            return {"response": "The AI assistant is currently disabled. Please enable it by setting ENABLE_LOCAL_LLM=true and restart the server."}

        with open("README.md", "r", encoding="utf-8") as f:
            project_context = f.read()

        # Enhance context with dynamic data (upcoming events)
        upcoming_events = db.query(models.Event)\
            .filter(models.Event.event_time >= datetime.utcnow())\
            .order_by(models.Event.event_time.asc()).all()
        
        if upcoming_events:
            events_summary = "\n\n### Upcoming Events:\n"
            for event in upcoming_events:
                events_summary += f"- {event.name} on {event.event_time.strftime('%Y-%m-%d %H:%M')} UTC\n"
            project_context += events_summary
        
        response = await llm_integration.generate_chatbot_response(llm_pipeline, chat_req.query, project_context)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chatbot error: {str(e)}")

# Mount the 'public' directory to serve the static frontend.
# This must be placed AFTER all the API routes.
app.mount("/", StaticFiles(directory="public", html=True), name="static")