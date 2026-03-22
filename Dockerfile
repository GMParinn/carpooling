FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create static and media directories
RUN mkdir -p /app/staticfiles /app/static

# Collect static files
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "carpooling.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
