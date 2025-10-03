from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import re
from . import llm_integration, messaging, models, schemas
from .database import SessionLocal
# Import the scheduler object and the global LLM pipeline reference
from .scheduler import scheduler 

async def process_registration(db: Session, user: models.User, event_id: int, llm_pipeline):
    """
    Handles the entire registration workflow.
    1. Creates registration record for an existing user.
    2. Sends immediate welcome message.
    3. Returns the user and the event.
    """
    # 1. Find the event
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise ValueError("Event not found")

    # --- Engagement Pattern Tracking ---
    # Refine user interests based on the event they are registering for.
    # This is a simple keyword extraction; a more advanced system could use NLP.
    existing_interests = set(re.split(r'[,;\s]+', user.interests.lower())) if user.interests else set()
    event_keywords = set(re.split(r'[,;\s]+', (event.name + " " + event.description).lower()))
    # A simple stop-word list to filter out common noise
    stop_words = {'a', 'an', 'the', 'in', 'on', 'for', 'and', 'with', 'to', 'is', 'of', 'it'}
    new_interests = {kw for kw in event_keywords if len(kw) > 2 and kw not in stop_words}
    
    user.interests = ", ".join(sorted(list(existing_interests.union(new_interests))))

    # Check if already registered
    existing_registration = db.query(models.Registration).filter_by(user_id=user.id, event_id=event.id).first()
    if existing_registration:
        raise ValueError("User is already registered for this event")

    # 2. Create the registration record
    db_registration = models.Registration(
        user_id=user.id,
        event_id=event.id,
        registration_time=datetime.utcnow()
    )
    db.add(db_registration)
    db.commit()
    db.refresh(user) # Refresh user to get the updated interests

    # 3. Send instant welcome message
    welcome_content = await llm_integration.generate_personalized_content(llm_pipeline, user, event, 'welcome')
    messaging.send_message(user.id, welcome_content)

    return user, event

def send_scheduled_message(user_id: int, event_id: int, message_type: str, llm_pipeline):
    """
    A job function for the scheduler. It generates personalized content and sends it.
    This function runs in a separate thread, so it needs its own DB session.
    """
    print(f"⚙️ Running scheduled job: '{message_type}' for user {user_id}, event {event_id}")
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.id == user_id).one()
        event = db.query(models.Event).filter(models.Event.id == event_id).one()

        # Because the LLM pipeline is async, we need to run it in a threadpool.
        # However, since APScheduler runs this in a thread already, we can call it
        # directly if we can get an event loop. A better long-term solution would be
        # to use a dedicated background task runner like Celery or ARQ.
        # For this project, we'll create a simple sync wrapper.
        import asyncio
        content = asyncio.run(llm_integration.generate_personalized_content(llm_pipeline, user, event, message_type))
        messaging.send_message(user.id, content)
    finally:
        db.close()


def schedule_all_communications(user_id: int, event_id: int, llm_pipeline):
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
        
        # Schedule content preview (e.g., 3 days before)
        preview_time = event.event_time - timedelta(days=3)
        if preview_time > now:
            job_id_preview = f"preview_{user_id}_{event_id}"
            scheduler.add_job(send_scheduled_message, 'date', run_date=preview_time, args=[user_id, event_id, 'content_preview', llm_pipeline], id=job_id_preview)

        # Schedule 24-hour reminder
        reminder_24h_time = event.event_time - timedelta(hours=24)
        if reminder_24h_time > now:
            job_id_24h = f"reminder_24h_{user_id}_{event_id}"
            scheduler.add_job(send_scheduled_message, 'date', run_date=reminder_24h_time, args=[user_id, event_id, 'reminder_24h', llm_pipeline], id=job_id_24h)

        # Schedule 1-hour reminder
        reminder_1h_time = event.event_time - timedelta(hours=1)
        if reminder_1h_time > now:
            job_id_1h = f"reminder_1h_{user_id}_{event_id}"
            scheduler.add_job(send_scheduled_message, 'date', run_date=reminder_1h_time, args=[user_id, event_id, 'reminder_1h', llm_pipeline], id=job_id_1h)

        # Schedule post-event follow-up (e.g., 2 hours after)
        follow_up_time = event.event_time + timedelta(hours=2)
        job_id_follow_up = f"follow_up_{user_id}_{event_id}"
        scheduler.add_job(send_scheduled_message, 'date', run_date=follow_up_time, args=[user_id, event_id, 'follow_up', llm_pipeline], id=job_id_follow_up)
    finally:
        db.close()