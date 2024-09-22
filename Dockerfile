# syntax=docker/dockerfile:1
# Use a base image with Python installed
FROM python:3.10

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-dev libpng-dev libjpeg-dev p7zip-full python3-pyqt5 unrar-free libgl1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /usr/local/bin

# Clone KCC from GitHub
RUN git clone https://github.com/ciromattia/kcc.git

# Upgrade pip and install all requirements
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install cmake && \
    python3 -m pip install -r kcc/requirements.txt

# Install Kindlegen
RUN wget https://archive.org/download/kindlegen_linux_2_6_i386_v2_9/kindlegen_linux_2.6_i386_v2_9.tar.gz && \
    tar -xf kindlegen_linux_2.6_i386_v2_9.tar.gz "kindlegen" && \
    chmod +rwx 'kindlegen' && rm kindlegen_linux_2.6_i386_v2_9.tar.gz

# Set the working directory for your app
WORKDIR /app

# Install ebookmanager dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python script into the container
COPY main.py /app/

# Run the Python script
CMD ["python3", "main.py"]
