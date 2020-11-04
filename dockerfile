FROM python:3.7

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
EXPOSE 5000
EXPOSE 5500

RUN mkdir /code
WORKDIR /code
ADD requirements.txt /code/
RUN pip install -r requirements.txt
RUN apt-get update
RUN apt-get install net-tools
RUN mkdir /code/fogify/
ADD agent /code/fogify/agent
ADD controller /code/fogify/controller
ADD connectors /code/fogify/connectors
ADD models /code/fogify/models
ADD utils /code/fogify/utils
ADD main.py /code/fogify/



# COPY ./installation/controller/entrypoint.sh /code/entrypoint.sh
# RUN chmod +x /code/entrypoint.sh
# ENTRYPOINT ["/code/entrypoint.sh"]