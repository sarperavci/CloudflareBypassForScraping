# Use a base image with Python and necessary tools
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y \
       wget \
       curl \
       gnupg \
       libgconf-2-4 \
       libnss3 \
       libx11-xcb1 \
       libxcomposite1 \
       libxdamage1 \
       libxrandr2 \
       libxi6 \
       libxtst6 \
       libappindicator3-1 \
       fonts-liberation \
       libasound2 \
       libatspi2.0-0 \
       libgdk-pixbuf2.0-0 \
       libgtk-3-0 \
       xdg-utils \
       libu2f-udev \
       libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

# Install Chromium browser
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg -i google-chrome-stable_current_amd64.deb \
    && apt-get -f install -y \
    && rm google-chrome-stable_current_amd64.deb

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
COPY server_requirements.txt .

RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install -r server_requirements.txt \
    && pip install uvicorn

# Copy the application code
COPY . .

# Expose the port FastAPI will run on
EXPOSE 8000

# Run the application with Uvicorn
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]