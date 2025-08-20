FROM ubuntu:24.04

RUN apt-get update -y \
  && apt-get install -y curl git \
  && curl https://install.fuel.network | sh

ENV PATH="${PATH}:/root/.fuelup/bin"

RUN fuelup toolchain install testnet \
  && fuelup default testnet

RUN mkdir -p /var/lib/fuel/config \
  && curl -L -o /var/lib/fuel/config/chain_config.json https://github.com/FuelLabs/fuel-core/raw/9fddeccb4d112c148f6793bc3d21131a13778a25/bin/fuel-core/chainspec/testnet/chain_config.json \
  && curl -L -o /var/lib/fuel/config/metadata.json https://github.com/FuelLabs/fuel-core/raw/9fddeccb4d112c148f6793bc3d21131a13778a25/bin/fuel-core/chainspec/testnet/metadata.json \
  && curl -L -o /var/lib/fuel/config/state_config.json https://github.com/FuelLabs/fuel-core/raw/9fddeccb4d112c148f6793bc3d21131a13778a25/bin/fuel-core/chainspec/testnet/state_config.json \
  && curl -L -o /var/lib/fuel/config/state_transition_bytecode.wasm https://github.com/FuelLabs/fuel-core/raw/9fddeccb4d112c148f6793bc3d21131a13778a25/bin/fuel-core/chainspec/testnet/state_transition_bytecode.wasm

