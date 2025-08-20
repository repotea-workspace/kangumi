FROM ubuntu:24.04

RUN apt-get update -y \
  && apt-get install -y curl bzip2 \
  && curl -L -o arteland.tar.gz https://github.com/artela-network/artela/releases/download/v0.4.7-rc6/artelad_0.4.7_rc6_Linux_amd64.tar.gz \
  && tar -xvf ./arteland.tar.gz -C ./ \
  && mv ./artelad /usr/local/bin/ \
  && rm -rf *.gz 

ENTRYPOINT ["/usr/local/bin/artelad"]
