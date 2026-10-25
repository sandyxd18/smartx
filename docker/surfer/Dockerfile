# Build the Surfer waveform viewer for the web (WASM) at a pinned tag.
#
# Surfer releases only ship native binaries; the web build exists only as a CI artifact
# that expires after an hour. So we build it the same way Surfer's CI job `pages_build`
# does (see .gitlab-ci.yml at the tag) and export the result:
#
#   docker build -f docker/surfer/Dockerfile --output type=local,dest=frontend/public/surfer .
#
# Use `make surfer` instead of calling this directly.

FROM rust:1.99.1-bookworm AS build

ARG SURFER_VERSION=v0.7.0
ARG TRUNK_VERSION=v0.21.14

RUN apt-get update && apt-get install -y --no-install-recommends python3-dev \
    && rm -rf /var/lib/apt/lists/*
RUN rustup target add wasm32-unknown-unknown
RUN curl -fsSL "https://github.com/trunk-rs/trunk/releases/download/${TRUNK_VERSION}/trunk-x86_64-unknown-linux-gnu.tar.gz" \
    | tar -xz -C /usr/local/bin trunk

RUN git clone --depth 1 --branch "${SURFER_VERSION}" --recurse-submodules --shallow-submodules \
        https://gitlab.com/surfer-project/surfer.git /src
WORKDIR /src

# trunk cannot emit relative URLs; build with a dummy prefix and rewrite it (as upstream CI).
RUN RUSTFLAGS="--cfg=web_sys_unstable_apis" trunk build --config=surfer/Trunk.toml index.html \
        --release --public-url /dist --features accesskit \
    && sed -i "s|/dist/|./|g" surfer/dist/index.html \
    && echo "${SURFER_VERSION}" > surfer/dist/SURFER_VERSION

FROM scratch
COPY --from=build /src/surfer/dist/ /
