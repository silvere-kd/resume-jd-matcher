# backend/celeryconfig.py

# redis is in another docker container
# if it's not the case for you,
# use : "redis://localhost:6379/0"

broker_url = "redis://host.docker.internal:6379/0"   
result_backend = "redis://host.docker.internal:6379/0"
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "UTC"
enable_utc = True
