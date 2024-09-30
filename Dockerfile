# Use the official Ubuntu image as the base image
FROM ubuntu:22.04

# Set environment variables to avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive
ENV DOCKERMODE=true

# Install necessary packages for Xvfb and pyvirtualdisplay
RUN apt-get update && \
    apt-get install -y \
    python3 \
    python3-pip \
    wget \
    gnupg \
    ca-certificates \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    libnss3 \
    git \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    x11-apps \
    fonts-liberation \
    libappindicator3-1 \
    libu2f-udev \
    libvulkan1 \
    libdrm2 \
    xdg-utils \
    xvfb \
    chromium-browser \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies including pyvirtualdisplay
RUN pip3 install --upgrade pip
RUN pip3 install pyvirtualdisplay

# Set up a working directory
WORKDIR /app

# Copy application files
RUN git clone https://github.com/sarperavci/CloudflareBypassForScraping .

# Install Python dependencies
RUN pip3 install -r requirements.txt
RUN pip3 install -r server_requirements.txt

# Expose the port for remote debugging
EXPOSE 9222

# Expose the port for the FastAPI server
EXPOSE 8000

ENTRYPOINT [ "git", "pull" ]
# Default command
CMD ["python3", "server.py"]
