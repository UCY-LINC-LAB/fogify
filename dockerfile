FROM python:3.9

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update -y
RUN apt-get install -y git build-essential libncurses5-dev libslang2-dev gettext zlib1g-dev libselinux1-dev debhelper lsb-release pkg-config po-debconf autoconf automake autopoint libtool
# RUN git config --global url."https://git.kernel.org/".insteadOf git.kernel.org:
# RUN git clone http://git.kernel.org/pub/scm/utils/util-linux/util-linux.git util-linux
# WORKDIR util-linux/
RUN apt-get install -y bison util-linux iproute2

# RUN ./autogen.sh
# RUN ./configure --without-python --disable-all-programs --enable-nsenter
# RUN make

# RUN cp /util-linux/nsenter /usr/local/bin/
# RUN cp /util-linux/bash-completion/nsenter /etc/bash_completion.d/nsenter


EXPOSE 5000
EXPOSE 5500
run /usr/local/bin/python -m pip install --upgrade pip
RUN curl -L "https://github.com/docker/compose/releases/download/1.27.4/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
RUN chmod +x /usr/local/bin/docker-compose
USER root
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y tshark
RUN mkdir /code
WORKDIR /code
ADD requirements.txt /code/
RUN pip3 install -r requirements.txt
RUN apt-get update
RUN apt-get install net-tools
RUN apt-get install -y iptables
RUN mkdir /code/fogify/
ADD agent /code/fogify/agent
ADD controller /code/fogify/controller
ADD connectors /code/fogify/connectors
ADD FogifyModel /code/fogify/FogifyModel
ADD utils /code/fogify/utils
ADD main.py /code/fogify/

ADD controller-entrypoint.sh /code/
ADD agent-entrypoint.sh /code/