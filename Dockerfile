FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# SQLite database + logs should persist across deploys when possible —
# mount a volume at /app/data and set DATABASE_PATH=/app/data/jobsnipr.db
RUN mkdir -p /app/data

CMD ["python", "main.py"]
