from apscheduler.schedulers.background import BackgroundScheduler

# Using a timezone-aware scheduler is best practice
scheduler = BackgroundScheduler(timezone="UTC", daemon=True)