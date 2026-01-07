# Use an official Python runtime as a parent image
# 3.10-slim is a good balance between size and compatibility for geospatial libs
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for geospatial libraries (GDAL, GEOS, PROJ)
# We also need 'build-essential' for compiling some python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libgdal-dev \
    gdal-bin \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables to help Python find GDAL
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Expose port 8501 for Streamlit
EXPOSE 8501

# Run app.py when the container launches
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
