from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from . import llm_integration, messaging, models, schemas
from .database import SessionLocal
# Import the scheduler object directly from the scheduler module
from .scheduler import scheduler 

def process_registration(db: Session, registration_data: schemas.RegistrationCreate):
    """
    Handles the entire registration workflow.
    1. Finds or creates user.
    2. Creates registration record.
    3. Sends immediate welcome message.
    4. Returns the created user and the event.
    """
    # 1. Find or create the user
    user = db.query(models.User).filter(models.User.email == registration_data.user.email).first()
    if not user:
        user = models.User(**registration_data.user.dict())
        db.add(user)
        db.commit()
        db.refresh(user)

    # 2. Find the event
    event = db.query(models.Event).filter(models.Event.id == registration_data.event_id).first()
    if not event:
        raise ValueError("Event not found")

    # 3. Create the registration record
    db_registration = models.Registration(
        user_id=user.id,
        event_id=event.id,
        registration_time=datetime.utcnow()
    )
    db.add(db_registration)
    db.commit()

    # 4. Send instant welcome message
    welcome_content = llm_integration.generate_personalized_content(user, event, 'welcome')
    messaging.send_message(user.id, welcome_content)

    return user, event

def schedule_all_communications(user_id: int, event_id: int):
    """
    Schedules reminder and follow-up jobs with APScheduler.
    Creates its own database session to ensure thread safety.
    """
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.id == user_id).one()
        event = db.query(models.Event).filter(models.Event.id == event_id).one()

        print(f"🗓️  Scheduling communications for {user.email} for event '{event.name}'")

        now = datetime.utcnow()
        
        # Schedule 24-hour reminder
        reminder_24h_time = event.event_time - timedelta(hours=24)
        if reminder_24h_time > now:
            content = llm_integration.generate_personalized_content(user, event, 'reminder_24h')
            scheduler.add_job(messaging.send_message, 'date', run_date=reminder_24h_time, args=[user.id, content])

        # Schedule 1-hour reminder
        reminder_1h_time = event.event_time - timedelta(hours=1)
        if reminder_1h_time > now:
            content = llm_integration.generate_personalized_content(user, event, 'reminder_1h')
            scheduler.add_job(messaging.send_message, 'date', run_date=reminder_1h_time, args=[user.id, content])

        # Schedule post-event follow-up (e.g., 2 hours after)
        follow_up_time = event.event_time + timedelta(hours=2)
        content = llm_integration.generate_personalized_content(user, event, 'follow_up')
        scheduler.add_job(messaging.send_message, 'date', run_date=follow_up_time, args=[user.id, content])
    finally:
        db.close()