FROM python:3.6-slim

RUN apt-get update \
    && apt-get -y install libpq-dev gcc \
    && pip install psycopg2
    
RUN mkdir -p /usr/src
WORKDIR /usr/src

COPY . /usr/src/

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT [ "python" ]

CMD [ "main.py" ]

