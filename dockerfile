FROM python:3.12.6-bookworm

RUN mkdir -p /usr/src/bot
WORKDIR /usr/src/bot

COPY . .

RUN pip install -r requirements.txt

CMD [ "python", "-u", "run_bot.py"]
