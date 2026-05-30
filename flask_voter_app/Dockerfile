# Use the official Python image from the Docker Hub
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Set environment variables
ENV FLASK_ENV=development

# Expose the port the FastAPI app runs on
EXPOSE 4434

# Command to run the application (Flask retired in Phase 4.5.b — uvicorn serves all)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "4434"]
