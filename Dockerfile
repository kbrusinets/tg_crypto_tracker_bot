FROM python:3.9

EXPOSE 8000

COPY . /tmp/main

WORKDIR "/tmp/main"

RUN pip install -r requirements.txt

RUN apt update && apt -y install postgresql-client