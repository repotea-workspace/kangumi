# This docker container will run until a given port is open

[![Docker Pulls](https://img.shields.io/docker/pulls/igops/wait-for-port?logo=docker)](https://hub.docker.com/r/igops/wait-for-port)

A tiny (~3MB) netcat-driven docker image which continuously tries connecting to a specified TCP/IP endpoint, and exits when the connection is established. Running it in the foreground allows blocking the execution of some context (e.g., deploy script), unless dependent services are up.

## Usage
```shell
$ docker run --rm igops/wait-for-port HOST PORT [POST_SUCCESS_WAIT]
```

- `HOST` and `PORT` point to the endpoint to monitor.
- `POST_SUCCESS_WAIT` (optional) adds a grace period in seconds after the port becomes reachable, allowing dependent services to settle before this container exits.

Environment variables let you control how aggressive the checks are and when the container should give up (see table below). Example:
```shell
$ docker run --rm \
  -e CHECK_FREQUENCY=0.5 \
  -e MAX_WAIT_SECONDS=120 \
  igops/wait-for-port 172.17.0.1 80 5
```
This command checks `172.17.0.1:80` every `0.5s`, waits at most `120s`, then keeps the container around for `5s` after a successful connection:
```
Waiting for 172.17.0.1:80 (timeout 120 seconds)...
Port is open, waiting an extra 5 seconds...
OK
```

## Real-life scenarios
### Wait for a service on host OS to start accepting traffic
#### Wait for nginx:
```shell
#!/bin/sh
docker run --rm -d -p 80:80 nginx
docker run --rm --add-host="host:host-gateway" igops/wait-for-port host 80
curl -XGET 'http://localhost'
```
Output:
```
Waiting for host:80...OK
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
...
```

#### Wait for sshd:
```shell
#!/bin/sh
docker run --rm --add-host="host:host-gateway" igops/wait-for-port host 22
echo "SSH server is running"
```

### Waiting for another container to start accepting traffic
#### From the same docker network:
```shell
#!/bin/sh
docker network create my-bridge
docker run --rm -d --net my-bridge --net-alias my-mongo mongo
docker run --rm --net my-bridge igops/wait-for-port my-mongo 27017
echo "MongoDB is up"
```

#### Using --publish:
```shell
#!/bin/sh
docker run --rm -d -p 27017:27107 mongo
docker run --rm --add-host="docker-host:host-gateway" igops/wait-for-port docker-host 27017
echo "MongoDB is up"
```

## ENV variables
| Variable        | Description                                                                                 |
|-----------------|---------------------------------------------------------------------------------------------|
| `CHECK_FREQUENCY`   | Port scanning frequency in seconds (defaults to `0.1`)                                      |
| `MAX_WAIT_SECONDS`  | Maximum number of seconds to wait before exiting with a non-zero status (defaults to `60`) |
