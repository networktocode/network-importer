
DOCKER_IMAGE = networktocode/network-importer
DOCKER_VER = 0.3.1

format:
	black --include "bin" .
	black .


# pyment -w -o google --first-line false --ignore-private false network_importer

check-format:
	black --check --include "bin" .
	black --check .

unit-tests:
	pytest -v .

start-batfish:
	docker run -d -p 9997:9997 -p 9996:9996 batfish/batfish 

tests: check-format unit-tests

build:
	docker build -t $(DOCKER_IMAGE):$(DOCKER_VER) .

.PHONY: lint
lint:
	@echo "Starting  lint"
# Verify all Python files pass pylint
	docker run -v $(shell pwd):/source $(DOCKER_IMAGE):$(DOCKER_VER) make pylint
# Verify all Python files meet Black code style
	docker run -v $(shell pwd):/source $(DOCKER_IMAGE):$(DOCKER_VER) black --check ./
# Verify all python files pass the Bandit security scanner
	docker run -v $(shell pwd):/source $(DOCKER_IMAGE):$(DOCKER_VER) bandit -r ./ -c .bandit
	@echo "Completed lint"

# Using to pass arguments to pylint that would fail in docker run command
.PHONY: pylint
pylint:
	find ./ -name "*.py" | xargs pylint