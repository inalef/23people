# Dockerfile
FROM python:3.8-slim

#RUN apt-get update -y
#RUN apt-get install -y python-pip python-dev build-essential
# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./
RUN pip install -r requirements.txt
ENV PORT 50001
EXPOSE $PORT
ENV FLASK_APP=main.py
CMD flask run --port=$PORT --host=0.0.0.0