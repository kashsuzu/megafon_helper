FROM python:3.14-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create volumes directories
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Define volumes for persistent data
VOLUME ["/app/data"]

# Run the application
CMD ["python", "main.py"]
