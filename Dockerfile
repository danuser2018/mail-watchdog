FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY ./src /app/src

# Default environment variables
ENV MAIL_SHARED_DIR=/shared/mail
ENV LOG_LEVEL=INFO

# Run the daemon service
CMD ["python", "src/main.py"]
