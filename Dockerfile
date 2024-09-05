# Use a base image with Python installed
FROM python:3.11-slim

# Set environment variables
ENV BOOK_MONITORING=true
ENV MANGA_MONITORING=true

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python script into the container
COPY main.py /app/

# Run the Python script
CMD ["python", "main.py"]
