from python:3.7.5

RUN pip install --upgrade pip

RUN mkdir /source
COPY . /source
WORKDIR /source
RUN python setup.py develop

RUN mkdir /library
WORKDIR /library
RUN git clone --single-branch --branch dga-nxos-xcvr https://github.com/dgarros/ntc-templates.git 
ENV NET_TEXTFSM=/library/ntc-templates