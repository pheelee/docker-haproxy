import os
import json
import random
import urllib2
import re
from bottle import Bottle, template, static_file


ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(ROOT_PATH, 'data')
CONFIG_FILE = os.path.join(DATA_PATH, 'links.txt')

app = Bottle()

title = os.environ.get('PORTAL_TITLE', 'The Portal')


def get_links():
    links = []
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            links = json.loads(f.read())
    return list(reversed(links))


@app.route('/')
def index():
    return template(os.path.join(ROOT_PATH, 'template.html'), title=title, apps=get_links())


@app.route('/favicon')
def favicon():
    return static_file('favicon.ico', root=os.path.join(ROOT_PATH, 'assets'))


@app.route('/assets/<type>/<filename>')
def assets(type, filename):
    return static_file(filename, root=os.path.join(ROOT_PATH, 'assets/%s' % type))


@app.route('/logo/<container_name>')
def logo(container_name):
    print('Serving logo')
    logo_path = os.path.join(ROOT_PATH, 'assets', 'logos')
    links = get_links()
    container = ''
    for l in links:
        if container_name in l['container']:
            container = l['container']
            break
    if container == '':
        return static_file('loader.gif', root=os.path.join(ROOT_PATH, 'assets', 'logos'))

    imgname = '%s.ico' % container_name
    if not os.path.isfile(os.path.join(logo_path, imgname)):
        try:
            r = urllib2.urlopen('http://%s' % container)
            html = r.read()
            favicon = re.findall('<link.*?icon.*?href=["\'](.*?)["\']', html)
            if len(favicon) > 0:
                url = 'http://%s/%s' % (container, favicon[0].lstrip('/'))
                r = urllib2.urlopen(url)
                with open(os.path.join(logo_path, imgname), 'wb') as f:
                    f.write(r.read())
            else:
                imgname = 'loader.gif'
        except urllib2.URLError:
            imgname = 'loader.gif'

    return static_file(imgname, root=os.path.join(ROOT_PATH, 'assets', 'logos'))


@app.route('/background')
def background():
    imgs = os.listdir(os.path.join(ROOT_PATH, 'assets', 'img'))
    return static_file(random.choice(imgs), root=os.path.join(ROOT_PATH, 'assets/img'))


if __name__ == '__main__':
    if not os.path.isdir(DATA_PATH):
        os.mkdir(DATA_PATH)
    app.run(server='paste')
