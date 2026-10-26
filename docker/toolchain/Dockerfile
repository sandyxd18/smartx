# Image "light" untuk job cepat: grading, simulasi, lint, sintesis + PnR FPGA.
# Toolchain digital diambil dari YosysHQ OSS CAD Suite (yosys, nextpnr,
# iverilog, verilator, openFPGALoader, apicula, dll.) supaya versinya baru
# dan konsisten. Tanggal rilis dipin lewat build arg (lihat Makefile/.env).
#
# Image ASIC (LibreLane + PDK) TIDAK dibangun di sini; lihat docs/phases/phase-5-asic.md.

# nextpnr-mistral (Cyclone V, for the DE1-SoC) is not part of OSS CAD Suite, so it is
# built here from pinned commits: nextpnr matches the nextpnr in the pinned OSS CAD Suite
# (0.11.1-79-g22c5adf4), Mistral is the nextpnr-latest branch the nextpnr README names.
FROM ubuntu:24.04 AS mistral
ARG NEXTPNR_COMMIT=22c5adf423ecb602dfc1250d10f740ccfff0786a
ARG MISTRAL_COMMIT=6a97d3e7e89d9830018904f184d4780b7bdae204
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git ca-certificates python3 python3-dev \
        libboost-dev libboost-filesystem-dev libboost-thread-dev \
        libboost-program-options-dev libboost-iostreams-dev \
        libeigen3-dev liblzma-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/Ravenslofty/mistral /opt/mistral \
    && git -C /opt/mistral checkout "$MISTRAL_COMMIT" \
    && git clone https://github.com/YosysHQ/nextpnr /opt/nextpnr \
    && git -C /opt/nextpnr checkout "$NEXTPNR_COMMIT" \
    && git -C /opt/nextpnr submodule update --init --recursive
RUN cmake -S /opt/nextpnr -B /opt/nextpnr/build -DARCH=mistral -DMISTRAL_ROOT=/opt/mistral \
        -DCMAKE_BUILD_TYPE=Release \
    && cmake --build /opt/nextpnr/build -j"$(nproc)" \
    && strip /opt/nextpnr/build/nextpnr-mistral

FROM ubuntu:24.04

ARG OSS_CAD_SUITE_DATE
ARG TARGETARCH=amd64
RUN test -n "$OSS_CAD_SUITE_DATE" || (echo "Set OSS_CAD_SUITE_DATE (mis. lewat 'make toolchain')" && false)

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl xz-utils make git python3 python3-venv \
        libpython3.12t64 \
    && rm -rf /var/lib/apt/lists/*

# OSS CAD Suite: nama file memakai tanggal tanpa tanda hubung.
RUN set -eux; \
    case "$TARGETARCH" in amd64) arch=x64 ;; arm64) arch=arm64 ;; *) echo "arch $TARGETARCH tidak didukung"; exit 1 ;; esac; \
    d="$(echo "$OSS_CAD_SUITE_DATE" | tr -d '-')"; \
    curl -fsSL -o /tmp/ocs.tgz \
      "https://github.com/YosysHQ/oss-cad-suite-build/releases/download/${OSS_CAD_SUITE_DATE}/oss-cad-suite-linux-${arch}-${d}.tgz"; \
    tar -xzf /tmp/ocs.tgz -C /opt; rm /tmp/ocs.tgz

# Pakai PATH langsung (bukan 'source environment') agar python3 sistem tetap dipakai
# untuk cocotb, sedangkan tool EDA dari OSS CAD Suite.
ENV PATH="/opt/venv/bin:/opt/oss-cad-suite/bin:${PATH}"

COPY tools/grader/requirements.txt /tmp/req.txt
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r /tmp/req.txt

# Verilator simulation compiles the model to C++ (g++); FST waveforms need lz4 and zlib.
# Separate layer after the OSS CAD Suite download, so adding it kept that layer cached.
RUN apt-get update && apt-get install -y --no-install-recommends \
        g++ liblz4-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# nextpnr-mistral from the stage above, with the Boost libraries it links against.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libboost-program-options1.83.0 libboost-thread1.83.0 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=mistral /opt/nextpnr/build/nextpnr-mistral /usr/local/bin/nextpnr-mistral

# Job berjalan sebagai user non-root; uid disesuaikan saat 'docker run --user'.
# ubuntu:24.04 sudah punya user 'ubuntu' dengan UID 1000; hapus dulu.
RUN (userdel -r ubuntu 2>/dev/null || true) && useradd -m -u 1000 smartx
WORKDIR /work
CMD ["bash"]
