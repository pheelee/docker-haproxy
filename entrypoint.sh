#!/bin/sh

HAPROXY_DIR=/usr/local/etc/haproxy

if [[ ! -d /usr/local/etc/haproxy/certs ]]; then
        mkdir $HAPROXY_DIR/certs
fi

if [[ ! -f /usr/local/etc/haproxy/haproxy.cfg ]]; then
    haproxy -f $HAPROXY_DIR/leproxy.cfg -p /run/haproxy.pid -D
fi

chmod +x /config/*.py

python /portal/portal.py &
python /config/GenerateHAProxyConfig.py $DEBUG


# Generate HAProxy Certs
#for site in `ls -1 /etc/letsencrypt/live`; do
#cat /etc/letsencrypt/live/$site/privkey.pem \
#  /etc/letsencrypt/live/$site/fullchain.pem \
#  | tee $HAPROXY_DIR/certs/haproxy-"$site".pem >/dev/null
#done
#
#haproxy -f $HAPROXY_DIR/haproxy.cfg -p /run/haproxy.pid -sf $(cat /run/haproxy.pid) -D
#/bin/sh
