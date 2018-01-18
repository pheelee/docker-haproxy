# Haproxy

simple automated reverse proxy for docker environments based on haproxy and LetsEncrypt!

## Supported tags

* `latest`
* `testing`

## Run

```bash
docker run -d \
-v cert-data:/etc/letsencrypt \
-v /var/run/docker.sock:/var/run/docker.sock \
-p "80:80" -p "443:443" \
--name haproxy \
pheelee/haproxy
```

## Usage

create a container and add a label named `RP_VIRTUAL_HOST` specifing the domain name and exposed container port to it.

**Example**:

`RP_VIRTUAL_HOST=foo.example.com:8080`

this generates a certificate (or adds the subdomain to an existing as SAN) for the domain foo.example.com and creates a reverse proxy entry for the container that owns the label. The port has to match the exposed port of the containers web application.

## Additional info

All HTTP requests are redirected to HTTPS!

If a new container with the label `RP_VIRTUAL_HOST` is created the following steps are automatically performed:

* Create or update an SSL Certificate
* Update HAProxy config
* Hot reconfigure HAProxy

## Portal

This container can generate a simple portal (frontend) for all its proxied applications (using PORTAL labels). To enable this feature you have to set the environment variable `PORTAL_URL` to a domain e.g portal.example.org

additionally you can customize the portal through the following variables

* `PORTAL_TITLE` : the heading title of the portal (default "The Portal")

### Entries

To have a container appear in portal set the following labels on it:

* Required: `PORTAL_NAME` : Name of the Container e.g "Portainer"
* Optional: `PORTAL_DESC` : small Description of the Container e.g "Docker Management Web Interface"
* Optional: `PORTAL_ICON` : Icon (if omitted the favicon from the app is used)

### Backgrounds

You can specify a randomly selected background by providing images in a volume binded folder

Example:

```bash
docker run -d \
-v cert-data:/etc/letsencrypt \
-v /var/run/docker.sock:/var/run/docker.sock \
-v ~/haproxy/background:/portal/assets/img \
-p "80:80" -p "443:443" \
--name haproxy \
pheelee/haproxy
```
