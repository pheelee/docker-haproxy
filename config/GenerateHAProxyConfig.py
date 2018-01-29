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


HAPROXY_TPL = '/usr/local/etc/haproxy/haproxy.cfg.tpl'
HAPROXY_CFG = '/usr/local/etc/haproxy/haproxy.cfg'

USE_PORTAL = False

CERT_PATH = '/etc/letsencrypt/live'
CERT_OUTPUT = '/usr/local/etc/haproxy/certs'
LABEL_HOOK = os.environ.get('LABEL_HOOK', 'RP_VIRTUAL_HOST')

client = docker.from_env()

CERTBOT_CMD = 'certbot certonly --standalone -d %s --non-interactive --expand --agree-tos --email %s --http-01-port 12888 --preferred-challenges http-01'

def get_rp_entry(entry):
    if entry.count(':') == 1 and type(int(entry.split(':')[1])) == int:
        return {
                'urls': [u.strip() for u in entry.split(':')[0].split(',')],
                'port': entry.split(':')[1],
                'tld': '.'.join(entry.split(':')[0].split('.')[-2:])
                }
    return None


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
        urls = portalurl.split(',')
        tld = '.'.join(urls[0].split('.')[-2:])
        email = 'webmaster@%s' % tld
        proxyconf[tld] = {'email': email, 'san': [{'container': '127.0.0.1:8080', 'url': url} for url in urls]}

    for c in client.containers():
        if LABEL_HOOK in c.get('Labels', {}):
            container_name = c['Names'][0].lstrip('/')
            cfg = get_rp_entry(c['Labels'][LABEL_HOOK])
            if cfg is None:
                print('Invalid %s entry for container: %s\nEntry:%s' % (LABEL_HOOK, container_name, c['Labels'][LABEL_HOOK]))
                continue
            email = 'webmaster@%s' % cfg['tld']
            try:
                a = socket.gethostbyname(container_name)
                if not cfg['tld'] in proxyconf:
                    proxyconf[cfg['tld']] = {'email': email, 'san':[]}
                for url in cfg['urls']:
                    if not url in proxyconf[cfg['tld']]['san']:
                        proxyconf[cfg['tld']]['san'].append({'container': '%s:%s' % (container_name, cfg['port']), 'url': url})
            except socket.gaierror:
                print('[ERROR] Could not resolve: %s, skipping host' % container_name)

            if 'PORTAL_NAME' in c.get('Labels', {}):
                portalcfg.append({
                    'container': '%s:%s' % (container_name, cfg['port']),
                    'link': 'https://%s' % cfg['urls'][0],
                    'logo': c['Labels'].get('PORTAL_ICON', '/logo/%s' % container_name),
                    'description': c['Labels'].get('PORTAL_DESC', ''),
                    'title': c['Labels']['PORTAL_NAME']
                    })

    if DEBUG is True: print(json.dumps(proxyconf, indent=4))

    if USE_PORTAL is True and DEBUG is False:
        # Create Portal Config
        with open('/portal/data/links.txt', 'w') as f:
            f.write(json.dumps(portalcfg))

    # Get Certificates
    for dom in proxyconf:
        cmd = CERTBOT_CMD % (','.join([p['url'] for p in proxyconf[dom]['san']]), proxyconf[dom]['email'])
        if DEBUG is True:
            print('Certbot cmd: ' + cmd)
        if not DEBUG:
            try:
                subprocess.check_output(cmd.split(' '))
            except subprocess.CalledProcessError:
                pass

        # Create Haproxy Config
        all_frontends += '\n    '.join(['use_backend %s if { hdr(host) -i %s }' % (p['url'], p['url']) for p in proxyconf[dom]['san']])
        all_backends += '\n'.join(['backend %s\n  server web1 %s\n' % (p['url'], p['container']) for p in proxyconf[dom]['san']])
        all_frontends += '\n    '
        all_backends += '\n'

    # Generate haproxy.cfg
    if os.path.isfile(HAPROXY_TPL):
        with open(HAPROXY_TPL, 'r') as f:
            config_tempalte = f.read()
        new_config = config_tempalte.replace('{{frontends}}', all_frontends).replace('{{backends}}', all_backends)
        if DEBUG is False:
            with open(HAPROXY_CFG, 'w') as f:
                f.write(new_config)
        else:
            print(new_config)

    if os.path.isdir(CERT_PATH) and DEBUG is False:
        if not os.path.isdir(CERT_OUTPUT):
            os.mkdir(CERT_OUTPUT)
        for site in os.listdir(CERT_PATH):
            output = ''
            with open(os.path.join(CERT_PATH, site, 'privkey.pem')) as f:
                output += f.read()
            with open(os.path.join(CERT_PATH, site, 'fullchain.pem')) as f:
                output += f.read()
            with open('%s/haproxy-%s.pem' % (CERT_OUTPUT, site), 'w') as f:
                f.write(output)

    if DEBUG is False:
        print("Restarting HAProxy")
        pid = []
        if os.path.isfile('/run/haproxy.pid'):
            with open('/run/haproxy.pid') as f:
                pid = ['-sf', str(int(f.read()))]
        try:
            cmd = ['haproxy', '-f', '/usr/local/etc/haproxy/haproxy.cfg', '-p',
                '/run/haproxy.pid', '-D', '-q'] + pid
            print(cmd)
            subprocess.check_output(cmd)
        except:
            pass

# Initially run Config Builder
build_config()

if DEBUG is True:
    print('Debug Mode on, skip listening for docker events')
    sys.exit(0)

print("Listening for Docker Events")
try:
    for event in client.events(filters={'event': 'create'}):
        ev_data = json.loads(event)
        if LABEL_HOOK in ev_data['Actor']['Attributes']:
            print("Discovered new Instance: %s" % ev_data['Actor']['Attributes']['name'])
            time.sleep(5)
            build_config()
except KeyboardInterrupt:
    print("Stop listending to Docker Events")
