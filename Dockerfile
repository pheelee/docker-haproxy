FROM haproxy:alpine
MAINTAINER Philipp Ritter <ritter.philipp@gmail.com>

EXPOSE 80
EXPOSE 443


RUN apk add --update --no-cache certbot py2-pip && \
    pip install docker-py && \
    rm -rf /var/cache/apk/*

COPY config /config
COPY haproxy.cfg.tpl leproxy.cfg /usr/local/etc/haproxy/
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /config/*.py

VOLUME /etc/letsencrypt

ENTRYPOINT /entrypoint.sh
