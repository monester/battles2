FROM python:3

COPY requirements.txt /

RUN pip install -r /requirements.txt

COPY ["battles", "scheduler", "manage.py", "static", "/app/"]

WORKDIR /app
COPY docker-entrypoint.sh /

ENTRYPOINT /docker-entrypoint.sh
