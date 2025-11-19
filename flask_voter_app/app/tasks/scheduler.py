# scheduler.py
from flask_apscheduler import APScheduler
from app.utils.election_utils import update_election_statuses

scheduler = APScheduler()


def init_scheduler(app):
    global scheduler
    if not scheduler.running:
        scheduler.init_app(app)
        scheduler.start()

    @scheduler.task("cron", id="update_election_statuses", hour=0, minute=0)
    def scheduled_update():
        with app.app_context():
            update_election_statuses()
