# ChipLab: perintah utama. Jalankan `make help`.
SHELL := /bin/bash
-include .env
export

TOOLCHAIN_IMAGE ?= chiplab/toolchain:local
PY ?= python3

.PHONY: help
help: ## Tampilkan daftar target
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n",$$1,$$2}'

.env:
	cp .env.example .env

.PHONY: pin-toolchain
pin-toolchain: .env ## Cari rilis OSS CAD Suite terbaru dan tulis ke .env
	@date=$$(curl -fsSL https://api.github.com/repos/YosysHQ/oss-cad-suite-build/releases/latest | $(PY) -c 'import json,sys;print(json.load(sys.stdin)["tag_name"])'); \
	 sed -i "s/^OSS_CAD_SUITE_DATE=.*/OSS_CAD_SUITE_DATE=$$date/" .env; \
	 echo "OSS_CAD_SUITE_DATE=$$date"

.PHONY: toolchain
toolchain: .env ## Build image toolchain (light)
	@test -n "$(OSS_CAD_SUITE_DATE)" || $(MAKE) pin-toolchain
	docker build -f docker/toolchain/Dockerfile \
		--build-arg OSS_CAD_SUITE_DATE=$$(grep ^OSS_CAD_SUITE_DATE .env | cut -d= -f2) \
		-t $(TOOLCHAIN_IMAGE) .

.PHONY: tool-versions
tool-versions: ## Cetak versi tool di dalam image toolchain
	docker run --rm $(TOOLCHAIN_IMAGE) bash -lc 'yosys -V; iverilog -V 2>&1 | head -1; verilator --version; nextpnr-himbaechel --version 2>&1 | head -1; python -c "import cocotb;print(\"cocotb\",cocotb.__version__)"'

.PHONY: check-content
check-content: ## Uji semua soal (solution lulus, starter gagal) di dalam image toolchain
	docker run --rm -v $(CURDIR):/work -w /work $(TOOLCHAIN_IMAGE) python tools/grader/check_content.py

.PHONY: check-content-local
check-content-local: ## Sama seperti check-content tapi pakai tool di host
	$(PY) tools/grader/check_content.py

# Target berikut diisi saat Fase 0 dikerjakan (lihat docs/phases/phase-0-fondasi.md).
.PHONY: dev test lint check
dev: ## Jalankan backend + frontend (docker compose)
	docker compose up --build

test: ## Unit test backend + frontend
	@echo "TODO(Fase 0): pytest backend + vitest frontend" && false

lint: ## Lint backend + frontend
	@echo "TODO(Fase 0): ruff + eslint" && false

check: lint test check-content ## Semua pemeriksaan; wajib hijau sebelum task dianggap selesai
