# syntax=docker/dockerfile:1
# Use a base image with Python installed
FROM python:3.12-slim-bullseye

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpng-dev libjpeg-dev p7zip-full unrar-free libgl1 jq build-essential cmake curl && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /usr/local/bin

# Clone kcc and install all requirements
RUN LATEST_TAG=$(curl -s "https://api.github.com/repos/ciromattia/kcc/releases/latest" | jq -rc ".tag_name") && \
    curl -L -o kcc.tar.gz https://github.com/ciromattia/kcc/archive/refs/tags/${LATEST_TAG}.tar.gz && \
    tar -xzf kcc.tar.gz && \
    mv kcc-* kcc && \
    rm kcc.tar.gz && \
    python3 -m pip install --upgrade pip && \
    python3 -m pip install -r kcc/requirements.txt

# Install Kindlegen
RUN curl -L -o kindlegen_linux_2.6_i386_v2_9.tar.gz https://archive.org/download/kindlegen_linux_2_6_i386_v2_9/kindlegen_linux_2.6_i386_v2_9.tar.gz && \
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
