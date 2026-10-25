# Image "light" untuk job cepat: grading, simulasi, lint, sintesis + PnR FPGA.
# Toolchain digital diambil dari YosysHQ OSS CAD Suite (yosys, nextpnr,
# iverilog, verilator, openFPGALoader, apicula, dll.) supaya versinya baru
# dan konsisten. Tanggal rilis dipin lewat build arg (lihat Makefile/.env).
#
# Image ASIC (LibreLane + PDK) TIDAK dibangun di sini; lihat docs/phases/phase-5-asic.md.

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

# Job berjalan sebagai user non-root; uid disesuaikan saat 'docker run --user'.
# ubuntu:24.04 sudah punya user 'ubuntu' dengan UID 1000; hapus dulu.
RUN (userdel -r ubuntu 2>/dev/null || true) && useradd -m -u 1000 smartx
WORKDIR /work
CMD ["bash"]
