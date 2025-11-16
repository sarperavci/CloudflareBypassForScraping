FROM ubuntu:rolling

# Set environment variables to avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive
# Install system dependencies for Chrome and Python packages
USER root
RUN apt-get update && apt-get install -y \
    software-properties-common \
    python3-pip \
    python3-venv \
    wget \
    gnupg \
    curl \
    xvfb \
    libgtk-3-0 \
    libgtk-3-dev \
    libxss1 \
    libxtst6 \
    libxrandr2 \
    libasound2t64 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libcairo-gobject2 \
    libgdk-pixbuf-2.0-0 \
    libdbus-glib-1-2 \
    libxt6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrender1 \
    libxi6 \
    fonts-liberation \
    libnss3 \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app
COPY . .
# Copy requirements.txt and install dependencies
COPY requirements.txt .

# Change ownership of app directory to ubuntu first
RUN chown -R ubuntu:ubuntu /app

# Switch to ubuntu user to create venv and install packages
USER ubuntu

# Create and activate virtual environment as ubuntu user
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install pip and requirements in virtual environment
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r server_requirements.txt

# Fetch Camoufox as ubuntu user
RUN camoufox fetch

# Switch back to root for remaining setup
USER root
WORKDIR /app


# Fix permissions for playwright_captcha addon directory (needs write access at runtime)
RUN chmod -R 777 /app/venv/lib/python*/site-packages/playwright_captcha/utils/camoufox_add_init_script/addon/ || true

# Switch to ubuntu user for runtime
USER ubuntu

# RUN the application
CMD ["python3", "server.py"]