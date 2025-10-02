from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

from . import models, schemas, services, database, scheduler

# Create database tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="Event & Webinar Engagement Booster",
    description="An AI-powered agent to boost event engagement.",
    version="1.0.0"
)

# Add CORS middleware to allow the front-end to communicate with the backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Event & Webinar Engagement Booster API. Go to /docs to see the API documentation."}

@app.on_event("startup")
def startup_event():
    scheduler.scheduler.start()
    print("🚀 Scheduler started.")

@app.on_event("shutdown")
def shutdown_event():
    scheduler.scheduler.shutdown()
    print("Scheduler shut down.")

@app.post("/events/", response_model=schemas.EventBase)
def create_event(event: schemas.EventCreate, db: Session = Depends(database.get_db)):
    """
    Create a new event in the database.
    """
    db_event = models.Event(**event.dict())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

@app.post("/register/", response_model=schemas.RegistrationResponse)
def register_for_event(registration: schemas.RegistrationCreate, db: Session = Depends(database.get_db)):
    """
    Register a user for an event.
    This endpoint triggers the entire engagement workflow:
    1. Creates user and registration records.
    2. Sends an instant welcome message.
    3. Schedules personalized reminders and a follow-up.
    """
    try:
        user, event = services.process_registration(db, registration)
        services.schedule_all_communications(user.id, event.id)
        return {"message": "Registration successful and communications scheduled.", "user_email": user.email, "event_id": event.id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")