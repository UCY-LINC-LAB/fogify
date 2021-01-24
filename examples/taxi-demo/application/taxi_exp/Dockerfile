# Pull base image of latest Python 3.7.x
FROM python:3.6

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN git clone https://github.com/opsengine/cpulimit/
WORKDIR cpulimit
RUN make && cp src/cpulimit /usr/bin


RUN mkdir /code
WORKDIR /code
ADD requirements.txt /code/
RUN pip install -r requirements.txt

RUN apt-get update && apt-get install -y stress && apt-get -y install cron rsyslog


EXPOSE 8000
# cron tab
ADD ./code/ /code/
#ADD crontab /etc/cron.d/crontab_file
RUN chmod 0644 /code/cronjobs

#try to keep logs
RUN echo "cron.*				/var/log/cron.log" >> /etc/rsyslog.conf
RUN service rsyslog start
#ADD code/entrypoint.sh /code/
#COPY code/entrypoint.sh /code/entrypoint.sh
RUN chmod +x /code/entrypoint.sh
CMD ["/bin/bash", "/code/entrypoint.sh"]