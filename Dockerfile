FROM python:3.6-slim-stretch

ADD requirements.txt /
RUN apt-get update
RUN apt-get install -y git
RUN apt-get install 'ffmpeg'\
    'libsm6'\ 
    'libxext6'  -y
RUN pip install -r /requirements.txt
ADD . /app
RUN git clone https://github.com/gangaramstyle/BreatHeatDocker.git
RUN mv /BreatHeatDocker /app/
WORKDIR /app

EXPOSE 5000
CMD [ "python" , "app.py"]
