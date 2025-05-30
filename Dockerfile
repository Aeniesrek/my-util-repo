FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app 
COPY run.py .

EXPOSE 8080

CMD ["sh", "-c", "gunicorn --factory --bind 0.0.0.0:${PORT:-8080} --workers 1 --log-level debug app:create_app"]