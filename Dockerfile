FROM python:3.8
WORKDIR /app

COPY ./requirements.txt /app

ENV PYTHONUNBUFFERED 1

RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "Dizplayer.py"]