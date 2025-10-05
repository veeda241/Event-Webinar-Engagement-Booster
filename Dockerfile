# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables to prevent Python from writing .pyc files to disc and to buffer output
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Cloud Run automatically sets the PORT environment variable. We default to 8080.
EXPOSE 8080

# Command to run the application using uvicorn
# We bind to 0.0.0.0 to accept connections from outside the container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
