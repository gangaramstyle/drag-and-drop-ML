FROM python:3.6-slim-stretch

ADD requirements.txt /
RUN pip install -r /requirements.txt
RUN apt-get update
RUN apt-get install -y git

ADD . /app
RUN git clone https://github.com/gangaramstyle/BreatHeatDocker.git
WORKDIR /app

EXPOSE 5000
CMD [ "python" , "app.py"]
