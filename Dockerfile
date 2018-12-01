FROM python:3

ADD . /source/

RUN pip install -e /source 

