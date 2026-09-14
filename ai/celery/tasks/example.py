from ai.celery.cel_app import celery_app


@celery_app.task(name="example_task", queue="ai_queue")
def example_task():
    return {"status": "success", "message": "Task completed"}
