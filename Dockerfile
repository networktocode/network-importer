FROM python:3.7.7

RUN pip install --upgrade pip \
  && pip install poetry

RUN mkdir /source
COPY . /source
WORKDIR /source
RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi

WORKDIR /source

CMD /bin/bash