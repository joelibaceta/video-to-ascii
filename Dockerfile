FROM python:3

ADD . /source/

RUN pip3 install -e /source --install-option="--with-audio"

