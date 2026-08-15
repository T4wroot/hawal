FROM python:3.11-alpine

WORKDIR /app

RUN apk add --no-cache curl bash iputils

COPY . /app

EXPOSE 9090

CMD ["python3", "server.py", "--host", "0.0.0.0", "--port", "9090"]
