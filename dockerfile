# Use official Python image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY bot.py .
COPY message_reader_fs.py .
COPY .env .
COPY service-account-auth.json .

# Set the default command to run the bot
CMD ["python", "bot.py"]