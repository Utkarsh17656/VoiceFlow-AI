FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /app

# Copy the requirements file first for caching
COPY voxreach_ai/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port
EXPOSE 8000

# Start the application using uvicorn. 
# Render automatically injects the PORT environment variable.
CMD uvicorn voxreach_ai.main:app --host 0.0.0.0 --port ${PORT:-8000}
