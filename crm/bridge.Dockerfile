FROM python:3.12-slim

# no apt needed: pg8000 is pure-python, urllib is stdlib
RUN pip install --no-cache-dir pg8000==1.31.5

WORKDIR /app
COPY bridge.py chatflow.py ./

# sensible default cadence; env overrides everything else
ENV PYTHONUNBUFFERED=1 \
    BRIDGE_EVERY=60

CMD ["python", "bridge.py", "--listen", "--every", "60"]