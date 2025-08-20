FROM paritytech/srtool:1.69.0

ARG RUSTC_VERSION="1.69.0"
ENV RUSTC_VERSION=$RUSTC_VERSION

RUN . /home/builder/cargo/env \
  && rustup toolchain add ${RUSTC_VERSION} \
  && rustup target add wasm32-unknown-unknown --toolchain ${RUSTC_VERSION} \
  && rustup default ${RUSTC_VERSION}
