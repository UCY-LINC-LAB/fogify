FROM python:3.7

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update -y
RUN apt-get install -y git build-essential libncurses5-dev libslang2-dev gettext zlib1g-dev libselinux1-dev debhelper lsb-release pkg-config po-debconf autoconf automake autopoint libtool

RUN git clone git://git.kernel.org/pub/scm/utils/util-linux/util-linux.git util-linux
WORKDIR util-linux/
RUN apt-get install -y bison
RUN ./autogen.sh
RUN ./configure --without-python --disable-all-programs --enable-nsenter
RUN make

RUN cp /util-linux/nsenter /usr/local/bin/
RUN cp /util-linux/bash-completion/nsenter /etc/bash_completion.d/nsenter


EXPOSE 5000
EXPOSE 5500
run /usr/local/bin/python -m pip install --upgrade pip
RUN mkdir /code
WORKDIR /code
ADD requirements.txt /code/
RUN pip3 install -r requirements.txt
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