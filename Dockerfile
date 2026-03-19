# Use official Python 3.11 image
FROM python:3.11-slim

# ---------------- System Packages for WeasyPrint ----------------
RUN apt-get update && apt-get install -y \
    build-essential \
    libcairo2 \
    libpango-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    python3-cffi \
    && rm -rf /var/lib/apt/lists/*

# ---------------- Create app directory ----------------
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Upgrade pip and install requirements
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose port (Render injects $PORT)
ENV PORT 10000
EXPOSE $PORT

# Environment variables placeholders (Render dashboard)
ENV FLASK_ENV=production

# Start the app using gunicorn
CMD exec gunicorn app:app --bind 0.0.0.0:$PORT --workers 4 --threads 4