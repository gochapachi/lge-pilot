FROM python:3.12-slim

# compose build context = the compose file's dir (crm/) → plain relative paths
RUN pip install --no-cache-dir pg8000==1.31.5

WORKDIR /app
COPY bridge.py chatflow.py ./

ENV PYTHONUNBUFFERED=1

CMD ["python", "bridge.py", "--listen", "--every", "60"]