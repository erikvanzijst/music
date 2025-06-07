FROM python:3.12-slim-bookworm
LABEL description="Music player"
ENV DEBIAN-FRONTEND=noninteractive

RUN apt-get update -y
RUN apt-get install --fix-missing -y \
    nginx telnet procps unzip supervisor openssh-client curl less htop ffmpeg sqlite3 gcc python3-dev file

RUN mkdir -p /app/.streamlit /app/static
COPY docker/ /
COPY .streamlit /app/.streamlit
COPY static /app/static
COPY requirements.txt Music.py /app/

WORKDIR /app
RUN pip install -r requirements.txt

EXPOSE 8000
CMD ["/usr/bin/supervisord", "--nodaemon", "-c", "/etc/supervisord.conf"]
