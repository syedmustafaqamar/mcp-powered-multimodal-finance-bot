class CeleryConfig:
    task_serializer = "json"
    accept_content = ["json"]
    result_serializer = "json"
    timezone = "UTC"
    enable_utc = True
    task_track_started = True
    task_time_limit = 60 * 60
    task_soft_time_limit = 55 * 60
    worker_prefetch_multiplier = 1
    result_expires = 3600
    task_routes = {
        "process_ingestion": {"queue": "ai_queue"},
        "ai.rag.search": {"queue": "ai_queue"},
        "ai.rag.answer": {"queue": "ai_queue"},
    }
