from fastapi import FastAPI, Depends, HTTPException, Request, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import uuid
import shutil

from . import models, schemas, services, database, security, config
from . import importer
from .scheduler import scheduler
from . import llm_integration

UPLOAD_DIR = "public/uploads/images"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    print("--- Dropping all database tables... ---")
    models.Base.metadata.drop_all(bind=database.engine)
    print("--- Creating database tables (if they don't exist)...")
    models.Base.metadata.create_all(bind=database.engine)
    print("--- Database tables checked/created.")
    
    # Create upload directory
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    print(f"--- Upload directory '{UPLOAD_DIR}' checked/created. ---")

    print("--- Application Startup ---")
    # Conditionally load the heavy LLM based on the centralized settings.
    if config.settings.ENABLE_LOCAL_LLM:
        app.state.llm_pipeline = llm_integration.create_llm_pipeline()
    else:
        app.state.llm_pipeline = None
        print("⚠️  Local LLM is explicitly DISABLED. Using fallback templates.")
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
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate user and return a JWT access token.
    """
    user = security.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=config.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/health/")
async def health_check(request: Request):
    llm_status = "ok" if request.app.state.llm_pipeline is not None else "unavailable"
    return {"llm_status": llm_status}

@app.post("/upload-image/")
async def upload_image(file: UploadFile = File(...), current_user: schemas.User = Depends(security.get_current_admin_user)):
    """
    Upload an image file. (Admin only)
    """
    # Generate a unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    # Return the public URL of the file
    public_url = f"/uploads/images/{unique_filename}"
    return {"image_url": public_url}


@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate):
    """
    Create a new user.
    """
    return security.create_user(user=user)

@app.post("/events/", response_model=schemas.Event)
def create_event(
    event: schemas.EventCreate,
    db: Session = Depends(database.get_db),
    current_user: schemas.User = Depends(security.get_current_admin_user)
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
async def read_users_me(current_user: schemas.User = Depends(security.get_current_user)):
    """
    Get the details of the currently authenticated user.
    """
    return current_user

@app.put("/users/me", response_model=schemas.User)
def update_user_profile(
    user_update: schemas.UserUpdate,
    current_user: schemas.User = Depends(security.get_current_user)
):
    """Update the current user's profile information."""
    updated_user = security.update_user_profile(current_user.email, user_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

@app.put("/users/me/contact", response_model=schemas.User)
def update_user_contact(
    contact_update: schemas.ContactUpdate,
    current_user: schemas.User = Depends(security.get_current_user)
):
    """Update the current user's contact preferences."""
    updated_user = security.update_user_contact(current_user.email, contact_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

@app.get("/users/me/registrations", response_model=List[int])
async def get_my_registrations(current_user: schemas.User = Depends(security.get_current_user), db: Session = Depends(database.get_db)):
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
    
    job_types = ["preview", "reminder_24h", "reminder_1h", "start", "follow_up"]
    for reg in registrations:
        for job_type in job_types:
            job_id = f"{job_type}_{reg.user_id}_{reg.event_id}"
            try:
                if scheduler.get_job(job_id):
                    scheduler.remove_job(job_id)
                    print(f"✅ Canceled scheduled job: {job_id}")
            except Exception as e:
                # This can happen if the job has already run or was never scheduled, which is fine.
                print(f"ⓘ Could not cancel job {job_id} (it may have already run): {e}")

    # Delete associated registrations first to maintain foreign key integrity
    db.query(models.DetailedRegistration).filter(models.DetailedRegistration.event_id == event_id).delete()
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
    current_user: schemas.User = Depends(security.get_current_user)
):
    """
    Register the currently authenticated user for an event.
    This endpoint is protected and requires a valid JWT token.
    """
    try:
        llm_pipeline = request.app.state.llm_pipeline
        
        # Fetch the SQLAlchemy User model from the database
        user_db = db.query(models.User).filter(models.User.id == current_user.id).first()
        if not user_db:
            # User from token does not exist in DB, so create it.
            user_db = models.User(
                id=current_user.id,
                email=current_user.email,
                name=current_user.name,
                hashed_password="", # Not needed for registration, auth is via JSON
                job_title=current_user.job_title,
                is_admin=current_user.is_admin,
                interests=current_user.interests,
                preferred_contact_method=current_user.preferred_contact_method,
                phone_number=current_user.phone_number
            )
            db.add(user_db)
            db.commit()
            db.refresh(user_db)

        # The user is now passed from the token dependency
        user, event = await services.process_registration(db, user_db, registration_request.event_id, llm_pipeline)
        services.schedule_all_communications(user, event, llm_pipeline)
        return {"message": "Registration successful and communications scheduled.", "user_email": user.email, "event_id": event.id}
    except ValueError as e: # Catching specific, known errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

# --- Chatbot Endpoint ---
@app.post("/chatbot/")
async def chat_with_bot(fastapi_req: Request, chat_req: schemas.ChatRequest, db: Session = Depends(database.get_db)):
    """
    Handles chatbot conversations, including taking actions on behalf of the user.
    """
    import json
    
    # --- 1. Get User and Context ---
    current_user = None
    try:
        token = await oauth2_scheme(fastapi_req)
        if token:
            # We need the full User object from the DB, not just the schema from the token
            user_schema = security.get_user_from_token(token)
            current_user = db.query(models.User).filter(models.User.email == user_schema.email).first()
    except HTTPException:
        current_user = None

    llm_pipeline = fastapi_req.app.state.llm_pipeline
    if llm_pipeline is None:
        return {"response": "The AI assistant is currently disabled."}

    # --- 2. Build Context for the LLM ---
    with open("README.md", "r", encoding="utf-8") as f:
        project_context = f.read()
    
    upcoming_events = db.query(models.Event).filter(models.Event.event_time >= datetime.utcnow()).order_by(models.Event.event_time.asc()).all()
    if upcoming_events:
        project_context += "\n\n### Upcoming Events:\n" + "\n".join([f"- {event.name}" for event in upcoming_events])

    if current_user:
        user_registrations = services.get_user_registrations(db, current_user.id)
        if user_registrations:
            project_context += "\n\n### Your Upcoming Registered Events:\n" + "\n".join([f"- You are registered for '{event.name}'" for event in user_registrations])

    # --- 3. Get Action or Response from LLM ---
    llm_output_str = await llm_integration.generate_chatbot_response(llm_pipeline, chat_req.query, project_context)
    
    try:
        llm_json = json.loads(llm_output_str)
    except json.JSONDecodeError:
        return {"response": "I'm sorry, I had a little trouble processing that. Could you try again?"}

    # --- 4. Process Action or Return Conversational Response ---
    if 'action' in llm_json:
        if not current_user:
            return {"response": "You need to be logged in to do that. Please log in and try again."}

        action = llm_json.get("action")
        response_message = ""

        if action == "list_registrations":
            user_regs = services.get_user_registrations(db, current_user.id)
            if not user_regs:
                response_message = "You aren't registered for any upcoming events."
            else:
                event_list = "\n".join([f"- {event.name}" for event in user_regs])
                response_message = f"You are registered for the following upcoming events:\n{event_list}"

        elif action in ["register", "cancel"]:
            event_name = llm_json.get("event_name")
            if not event_name:
                return {"response": "I'm sorry, I didn't catch the event name. Could you please specify which event?"}
            
            event = services.find_event_by_name(db, event_name)
            if not event:
                return {"response": f"I couldn't find an event named '{event_name}'."}

            if action == "register":
                try:
                    _, registered_event = await services.process_registration(db, current_user, event.id, llm_pipeline)
                    services.schedule_all_communications(current_user, registered_event, llm_pipeline)
                    response_message = f"You've been successfully registered for {registered_event.name}! I've scheduled all the reminders for you."
                except ValueError as e:
                    response_message = str(e) # e.g., "User is already registered for this event"
            
            elif action == "cancel":
                if services.cancel_registration(db, current_user.id, event.id):
                    response_message = f"Your registration for {event.name} has been successfully canceled."
                else:
                    response_message = f"It doesn't look like you're registered for {event.name}."

        else:
            response_message = "I'm not sure how to do that. I can help with registering, canceling, or listing your events."
        
        return {"response": response_message}

    elif 'response' in llm_json:
        return {"response": llm_json['response']}
    else:
        return {"response": "I'm not sure how to respond to that, sorry!"}

@app.post("/detailed-register/", response_model=schemas.RegistrationResponse)
async def create_detailed_registration(
    request: Request,
    registration_data: schemas.DetailedRegistrationCreate,
    db: Session = Depends(database.get_db),
    current_user: schemas.User = Depends(security.get_current_user)
):
    """
    Create a new detailed registration for an event, and trigger the welcome messaging workflow.
    """
    # The logic is now very similar to the simple /register endpoint.
    try:
        llm_pipeline = request.app.state.llm_pipeline
        
        # Fetch the SQLAlchemy User model from the database
        user_db = db.query(models.User).filter(models.User.id == current_user.id).first()
        if not user_db:
            # This part is crucial for ensuring the user exists in our main `users` table
            # before we try to register them for an event.
            user_db = models.User(
                id=current_user.id,
                email=current_user.email,
                name=current_user.name,
                hashed_password="", # Not needed for registration, auth is via JSON
                job_title=current_user.job_title,
                is_admin=current_user.is_admin,
                interests=current_user.interests,
                preferred_contact_method=current_user.preferred_contact_method,
                phone_number=current_user.phone_number
            )
            db.add(user_db)
            db.commit()
            db.refresh(user_db)

        # Create the detailed registration record
        db_detailed_registration = models.DetailedRegistration(
            **registration_data.model_dump(),
            user_id=current_user.id,
            registration_time=datetime.utcnow()
        )
        db.add(db_detailed_registration)
        
        # Use the same robust registration and scheduling logic
        user, event = await services.process_registration(db, user_db, registration_data.event_id, llm_pipeline)
        services.schedule_all_communications(user, event, llm_pipeline)
        
        db.commit() # Commit the detailed registration and any updates from process_registration

        return {"message": "Registration successful and communications scheduled.", "user_email": user.email, "event_id": event.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Rollback in case of failure to avoid partial data
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

from sqlalchemy.orm import joinedload

@app.get("/registrations/{event_id}", response_model=List[schemas.RegistrationAnalysisDetail])
def read_detailed_registrations(
    event_id: int,
    db: Session = Depends(database.get_db),
    current_user: schemas.User = Depends(security.get_current_admin_user)
):
    """
    Retrieve all detailed registrations for a specific event, including related user data for analysis.
    (Admin only)
    """
    registrations = db.query(models.DetailedRegistration).options(joinedload(models.DetailedRegistration.user)).filter(models.DetailedRegistration.event_id == event_id).all()
    
    results = []
    for reg in registrations:
        if reg.user:
            analysis_data = schemas.RegistrationAnalysisDetail(
                id=reg.id,
                event_id=reg.event_id,
                user_id=reg.user_id,
                full_name=reg.full_name,
                email=reg.email,
                phone_number=reg.phone_number,
                payment_info=reg.payment_info,
                consent_agreed=reg.consent_agreed,
                team_details=reg.team_details,
                registration_time=reg.registration_time,
                job_title=reg.user.job_title,
                interests=reg.user.interests,
                preferred_contact_method=reg.user.preferred_contact_method
            )
            results.append(analysis_data)
    return results

# Mount the 'public' directory to serve the static frontend.
# This must be placed AFTER all the API routes.
app.mount("/", StaticFiles(directory="public", html=True), name="static")