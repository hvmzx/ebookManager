# Use a base image with Python installed
FROM python:3.10

# Set environment variables

WORKDIR /usr/local/bin
RUN git clone https://github.com/ciromattia/kcc.git
RUN python -m pip install --upgrade pip
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-dev python3-pip libpng-dev libjpeg-dev p7zip-full python3-pyqt5 unrar-free libgl1
RUN pip install cmake
RUN pip install -r kcc/requirements.txt

RUN wget https://archive.org/download/kindlegen_linux_2_6_i386_v2_9/kindlegen_linux_2.6_i386_v2_9.tar.gz
RUN tar -xf kindlegen_linux_2.6_i386_v2_9.tar.gz "kindlegen"
RUN chmod +rwx 'kindlegen'
RUN rm kindlegen_linux_2.6_i386_v2_9.tar.gz

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python script into the container
COPY main.py /app/

# Run the Python script
CMD ["python", "main.py"]