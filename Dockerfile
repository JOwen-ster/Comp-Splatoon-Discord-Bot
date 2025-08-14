FROM python:3.12.6-bookworm

# Set working directory
WORKDIR /usr/src/bot

# Copy only requirements first to leverage Docker caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the bot files
COPY . .

# Run bot with unbuffered output so logs appear immediately
CMD ["python", "-u", "run_bot.py"]
