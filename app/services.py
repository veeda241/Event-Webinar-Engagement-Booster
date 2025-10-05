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
    db.flush() # Use flush to send the registration to the DB and get an ID without ending the transaction.
    db.refresh(db_registration)
    db.refresh(user) # Refresh user to get the updated interests

    # 3. Send instant welcome message
    welcome_content = await llm_integration.generate_personalized_content(llm_pipeline, user, event, 'welcome')
    await messaging.send_message(user.id, welcome_content)

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
        asyncio.run(messaging.send_message(user.id, content))
    finally:
        db.close()


def schedule_all_communications(user: models.User, event: models.Event, llm_pipeline):
    """
    Schedules reminder and follow-up jobs with APScheduler.
    This function does not need its own database session as it receives the necessary objects.
    """
    print(f"🗓️  Scheduling communications for {user.email} for event '{event.name}'")

    now = datetime.utcnow()
    user_id = user.id
    event_id = event.id
    
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

    # Schedule "event starting now" nudge
    if event.event_time > now:
        job_id_start = f"start_{user_id}_{event_id}"
        scheduler.add_job(send_scheduled_message, 'date', run_date=event.event_time, args=[user_id, event_id, 'event_starting', llm_pipeline], id=job_id_start)

    # Schedule post-event follow-up (e.g., 2 hours after)
    follow_up_time = event.event_time + timedelta(hours=2)
    job_id_follow_up = f"follow_up_{user_id}_{event_id}"
    scheduler.add_job(send_scheduled_message, 'date', run_date=follow_up_time, args=[user_id, event_id, 'follow_up', llm_pipeline], id=job_id_follow_up)

def find_event_by_name(db: Session, event_name: str) -> models.Event | None:
    """Finds an event by its name, case-insensitively."""
    return db.query(models.Event).filter(models.Event.name.ilike(f"%{event_name}%")).first()

def get_user_registrations(db: Session, user_id: int) -> list[models.Event]:
    """Gets all upcoming events a user is registered for."""
    return db.query(models.Event).join(models.Registration).filter(
        models.Registration.user_id == user_id,
        models.Event.event_time >= datetime.utcnow()
    ).all()

def cancel_registration(db: Session, user_id: int, event_id: int) -> bool:
    """
    Cancels a user's registration for an event and removes all associated scheduled jobs.
    """
    # 1. Find the registration
    registration = db.query(models.Registration).filter_by(user_id=user_id, event_id=event_id).first()
    if not registration:
        return False # Or raise an error

    # 2. Find and remove all associated jobs from the scheduler
    # The job IDs were created with a predictable pattern: f"{job_type}_{user_id}_{event_id}"
    job_types = ["preview", "reminder_24h", "reminder_1h", "start", "follow_up"]
    for job_type in job_types:
        job_id = f"{job_type}_{user_id}_{event_id}"
        try:
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
                print(f"✅ Canceled scheduled job: {job_id}")
        except Exception as e:
            # This can happen if the job has already run or was never scheduled, which is fine.
            print(f"ⓘ Could not cancel job {job_id} (it may have already run): {e}")

    # 3. Delete the registration from the database
    db.delete(registration)
    db.commit()
    return True