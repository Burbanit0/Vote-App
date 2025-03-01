# Use the official Python image from the Docker Hub
FROM python:3.8-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Set environment variables
ENV FLASK_APP=app
ENV FLASK_ENV=development

# Expose the port the app runs on
EXPOSE 4433

# Command to run the application
CMD ["flask", "run", "--host=0.0.0.0", "--port=4433"]
