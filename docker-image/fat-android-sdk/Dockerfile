FROM androidsdk/android-31:latest

COPY . /opt

RUN apt update -y && \
  apt install -y maven git curl && \
  sdkmanager --package_file=/opt/requirement-deps.txt
