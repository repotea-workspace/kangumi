FROM ubuntu:24.04


RUN apt-get update -y \
  && apt-get install -y curl \
  && echo "#!/bin/bash" > /entrypoint.sh \
  && echo 'curl -sL1 https://nubit.sh | bash' >> /entrypoint.sh \
  && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
