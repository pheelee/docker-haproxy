FROM haproxy:alpine
MAINTAINER Philipp Ritter <ritter.philipp@gmail.com>

EXPOSE 80
EXPOSE 443

ENV PORTAL_URL none
ENV LABEL_HOOK RP_VIRTUAL_HOST

COPY config /config
COPY portal /portal
COPY haproxy.cfg.tpl leproxy.cfg /usr/local/etc/haproxy/
COPY entrypoint.sh /entrypoint.sh

RUN apk add --update --no-cache certbot py2-pip && \
    pip install docker-py && \
    pip install -r /portal/requirements.txt && \
    rm -rf /var/cache/apk/*

VOLUME /etc/letsencrypt
VOLUME /portal/assets/img

ENTRYPOINT /entrypoint.sh
