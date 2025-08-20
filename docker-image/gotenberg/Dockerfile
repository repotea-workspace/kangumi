FROM gotenberg/gotenberg:8.21

USER root

RUN apt-get update \
  && apt-get install -y fonts-noto-cjk fonts-arphic-uming fonts-wqy-zenhei \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

USER gotenberg
