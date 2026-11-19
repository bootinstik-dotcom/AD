FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py db.py run.py ./
ENV DB_PATH=/data/adservice.sqlite3
CMD ["python", "run.py"]
