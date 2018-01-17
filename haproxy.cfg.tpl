global
    maxconn 256
    ssl-default-bind-ciphers AES256+EECDH:AES256+EDH:!aNULL;
    tune.ssl.default-dh-param 4096

defaults
  log global
  mode http
  timeout connect 5000ms
  timeout client 50000ms
  timeout server 50000ms
  option forwardfor
  option http-server-close

frontend fe-haproxy
  bind *:80
  mode http

  acl letsencrypt-acl path_beg /.well-known/acme-challenge/
  redirect scheme https code 301 if !{ ssl_fc  }  !letsencrypt-acl
  use_backend letsencrypt-backend if letsencrypt-acl


frontend ft_ssl_vip
    bind *:443 ssl crt /usr/local/etc/haproxy/certs/ no-sslv3 no-tls-tickets no-tlsv10 no-tlsv11
    http-request set-header X-Forwarded-Proto https if { ssl_fc }
    rspadd Strict-Transport-Security:\ max-age=15768000

    {{frontends}}

{{backends}}

backend letsencrypt-backend
  server letsencrypt 127.0.0.1:12888
