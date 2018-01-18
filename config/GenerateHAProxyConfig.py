#!/usr/bin/python

import os
import re
import urllib2
import docker
import json
import subprocess
import sys
import time
import socket

DEBUG = len(sys.argv) > 1 and sys.argv[1] == 'DEBUG'

BASE_URL = 'http+unix://%s' % '/var/run/docker.sock'.replace('/', '%2F')
HAPROXY_TPL = '/usr/local/etc/haproxy/haproxy.cfg.tpl'
HAPROXY_CFG = '/usr/local/etc/haproxy/haproxy.cfg'

USE_PORTAL = False

CERT_PATH = '/etc/letsencrypt/live'

client = docker.from_env()

CERTBOT_CMD = 'certbot certonly --standalone -d %s --non-interactive --expand --agree-tos --email %s --http-01-port 12888 --preferred-challenges http-01'

def build_config():

    print("Scanning Environment and update config")
    proxyconf = {}
    portalcfg = []
    all_frontends = ''
    all_backends = ''

    # Check if Portal is enabled
    portalurl = os.environ.get('PORTAL_URL', '')
    if portalurl != '':
        USE_PORTAL = True
        tld = ''.join(portalurl.split('.')[-2:])
        email = 'webmaster@%s' % tld
        proxyconf[tld] = {'email': email, 'san': [{'container': '127.0.0.1:8080', 'url': portalurl}]}
    for c in client.containers():
        if 'RP_VIRTUAL_HOST' in c.get('Labels', {}):

            virtual_host = c['Labels']['RP_VIRTUAL_HOST']
            container_port = c['Labels']['RP_VIRTUAL_HOST'].split(':')[1]
            container_name = c['Names'][0].lstrip('/')
            container_url  = c['Labels']['RP_VIRTUAL_HOST'].split(':')[0]
            tld = '.'.join(virtual_host.split(':')[0].split('.')[-2:])
            email = 'webmaster@%s' % tld
            try:
                a = socket.gethostbyname(container_name)
                if not tld in proxyconf:
                    proxyconf[tld] = {'email': email, 'san':[]}
                if not container_url in proxyconf[tld]['san']:
                    proxyconf[tld]['san'].append({'container': '%s:%s' % (container_name, container_port), 'url': container_url})
            except socket.gaierror:
                print('[ERROR] Could not resolve: %s, skipping host' % container_name)

            if 'PORTAL_NAME' in c.get('Labels', {}):
                portalcfg.append({
                    'container': '%s:%s' % (container_name, container_port),
                    'link': 'https://%s' % container_url,
                    'logo': c['Labels'].get('PORTAL_ICON', '/logo/%s' % container_name),
                    'description': c['Labels'].get('PORTAL_DESC', ''),
                    'title': c['Labels']['PORTAL_NAME']
                    })


    if USE_PORTAL is True:
        # Create Portal Config
        with open('/portal/data/links.txt', 'w') as f:
            f.write(json.dumps(portalcfg))

    # Get Certificates
    for dom in proxyconf:
        cmd = CERTBOT_CMD % (','.join([p['url'] for p in proxyconf[dom]['san']]), proxyconf[dom]['email'])
        print('Certbot cmd: ' + cmd)
        if not DEBUG: subprocess.check_output(cmd.split(' '))

        # Create Haproxy Config
        all_frontends += '\n    '.join(['use_backend %s if { hdr_dom(host) -i %s }' % (p['url'], p['url']) for p in proxyconf[dom]['san']])
        all_backends += '\n'.join(['backend %s\n  server web1 %s\n' % (p['url'], p['container']) for p in proxyconf[dom]['san']])
        all_frontends += '\n    '
        all_backends += '\n'

    # Generate haproxy.cfg
    if os.path.isfile(HAPROXY_TPL):
        with open(HAPROXY_TPL, 'r') as f:
            config_tempalte = f.read()
        new_config = config_tempalte.replace('{{frontends}}', all_frontends).replace('{{backends}}', all_backends)
        with open(HAPROXY_CFG, 'w') as f:
            f.write(new_config)

    if os.path.isdir(CERT_PATH):
        for site in os.listdir(CERT_PATH):
            output = ''
            with open(os.path.join(CERT_PATH, site, 'privkey.pem')) as f:
                output += f.read()
            with open(os.path.join(CERT_PATH, site, 'fullchain.pem')) as f:
                output += f.read()
            with open('/usr/local/etc/haproxy/certs/haproxy-%s.pem' % site, 'w') as f:
                f.write(output)

    print("Restarting HAProxy")
    pid = ''
    if os.path.isfile('/run/haproxy.pid'):
        with open('/run/haproxy.pid') as f:
            pid = str(int(f.read()))
    try:
        subprocess.check_call(['haproxy', '-f', '/usr/local/etc/haproxy/haproxy.cfg', '-p',
            '/run/haproxy.pid', '-sf', pid, '-D', '-q'])
    except:
        pass

# Initially run Config Builder
build_config()

print("Listening for Docker Events")
try:
    for event in client.events(filters={'event': 'create'}):
        ev_data = json.loads(event)
        if 'RP_VIRTUAL_HOST' in ev_data['Actor']['Attributes']:
            print("Discovered new Instance: %s" % ev_data['Actor']['Attributes']['name'])
            time.sleep(5)
            build_config()
except KeyboardInterrupt:
    print("Stop listending to Docker Events")
