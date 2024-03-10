FROM python:3.11-slim-bookworm
LABEL description="Music player"
ENV DEBIAN-FRONTEND=noninteractive

RUN apt-get update -y
RUN apt-get install -y nginx telnet procps unzip supervisor openssh-client curl less htop ffmpeg sqlite3 gcc python3-dev
RUN mkdir /app
COPY docker/ /
COPY .streamlit /app
COPY requirements.txt /app
COPY Music.py /app

WORKDIR /app
RUN pip install -r requirements.txt

EXPOSE 8000
CMD ["/usr/bin/supervisord", "--nodaemon", "-c", "/etc/supervisord.conf"]
