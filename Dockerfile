FROM python:3.7.5

RUN pip install --upgrade pip
# RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python

RUN pip install poetry

RUN mkdir /source
COPY . /source
WORKDIR /source
RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi

RUN mkdir /library
WORKDIR /library
RUN git clone --single-branch --branch master https://github.com/networktocode/ntc-templates.git 
ENV NET_TEXTFSM=/library/ntc-templates

WORKDIR /source
RUN pip install -r requirements-develop.txt

CMD /bin/bash