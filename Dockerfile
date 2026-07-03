FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HOME=/home/user

# Create user 1000 for Hugging Face compatibility
RUN useradd -m -u 1000 user
WORKDIR $HOME/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY --chown=user:user . .

# Switch to the user
USER user

# Expose port 7860
EXPOSE 7860

# Run Flask app with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "1", "--threads", "4", "--timeout", "120", "server:app"]
