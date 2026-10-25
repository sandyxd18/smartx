# SmartX: perintah utama. Jalankan `make help`.
# Di Windows, pakai bash dari Git for Windows agar make bisa dipanggil dari
# PowerShell maupun Git Bash. Path 8.3 menghindari spasi di "Program Files".
ifeq ($(OS),Windows_NT)
GIT_BASH ?= C:/Progra~1/Git/bin/bash.exe
SHELL := $(GIT_BASH)
# Cegah MSYS mengubah path container (mis. /work) menjadi path Windows.
export MSYS_NO_PATHCONV := 1
else
SHELL := /bin/bash
endif
-include .env
export

TOOLCHAIN_IMAGE ?= smartx/toolchain:local
# Di Windows, 'python3' biasanya stub Microsoft Store; pakai 'python'.
ifeq ($(OS),Windows_NT)
PY ?= python
else
PY ?= python3
endif

.PHONY: help
help: ## Tampilkan daftar target
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n",$$1,$$2}'

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
	docker run --rm $(TOOLCHAIN_IMAGE) bash -lc 'yosys -V; iverilog -V 2>&1 | head -1; verilator --version; g++ --version | head -1; nextpnr-himbaechel --version 2>&1 | head -1; python -c "import cocotb;print(\"cocotb\",cocotb.__version__)"'

.PHONY: check-content
check-content: ## Uji semua soal (solution lulus, starter gagal) di dalam image toolchain
	docker run --rm -v $(CURDIR):/work -w /work $(TOOLCHAIN_IMAGE) python tools/grader/check_content.py

.PHONY: check-content-local
check-content-local: ## Sama seperti check-content tapi pakai tool di host
	$(PY) tools/grader/check_content.py

UV ?= uv
NPM ?= npm
SURFER_VERSION ?= v0.7.0

# Path repo menurut host Docker; dipakai compose untuk bind mount container job.
export SMARTX_HOST_DIR := $(CURDIR)
# Di Linux/macOS, file hasil run dimiliki user yang menjalankan make (bukan root).
ifneq ($(OS),Windows_NT)
ifeq ($(JOB_USER),)
ifneq ($(shell id -u),0)
export JOB_USER := $(shell id -u):$(shell id -g)
endif
endif
endif

frontend/node_modules: frontend/package-lock.json
	cd frontend && $(NPM) ci
	@touch $@

.PHONY: dev
dev: .env ## Jalankan backend + frontend (docker compose), buka http://127.0.0.1:8080
	@docker image inspect $(TOOLCHAIN_IMAGE) >/dev/null 2>&1 || \
		{ echo "Image $(TOOLCHAIN_IMAGE) belum ada. Jalankan 'make toolchain' dulu."; exit 1; }
	docker compose up --build --renew-anon-volumes

.PHONY: test test-backend test-frontend test-docker
test: test-backend test-frontend ## Unit test backend + frontend (tanpa Docker)

test-backend:
	cd backend && $(UV) run pytest -q

test-frontend: frontend/node_modules
	cd frontend && $(NPM) test

test-docker: ## Test integrasi job dengan Docker asli dan image toolchain
	cd backend && SMARTX_DOCKER_TESTS=1 $(UV) run pytest -q tests/integration

.PHONY: lint lint-backend lint-frontend
lint: lint-backend lint-frontend ## Lint + format + typecheck backend dan frontend

lint-backend:
	cd backend && $(UV) run ruff check . && $(UV) run ruff format --check .

lint-frontend: frontend/node_modules
	cd frontend && $(NPM) run lint && $(NPM) run typecheck && $(NPM) run gen:api -- --check

.PHONY: check
check: lint test test-docker check-content ## Semua pemeriksaan; wajib hijau sebelum task dianggap selesai

.PHONY: surfer
surfer: ## Build Surfer web (WASM) versi SURFER_VERSION ke frontend/public/surfer (lama, sekali saja)
	docker build -f docker/surfer/Dockerfile --build-arg SURFER_VERSION=$(SURFER_VERSION) \
		--output type=local,dest=frontend/public/surfer .
