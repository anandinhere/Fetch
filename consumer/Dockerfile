# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY app/ /app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make the Python script executable
RUN chmod +x consumer.py

# Set environment variable for Python
ENV PYTHONUNBUFFERED=1

# Run consumer.py when the container launches
ENTRYPOINT ["python", "consumer.py"]
