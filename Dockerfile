FROM haproxy:alpine
MAINTAINER Philipp Ritter <ritter.philipp@gmail.com>

EXPOSE 80
EXPOSE 443

ENV PORTAL_URL none

RUN apk add --update --no-cache certbot py2-pip && \
    pip install docker-py bottle && \
    rm -rf /var/cache/apk/*

COPY config /config
COPY portal /portal
COPY haproxy.cfg.tpl leproxy.cfg /usr/local/etc/haproxy/
COPY entrypoint.sh /entrypoint.sh

VOLUME /etc/letsencrypt
VOLUME /portal/assets/img

ENTRYPOINT /entrypoint.sh
