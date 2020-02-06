
DOCKER_IMAGE = networktocode/network-importer
DOCKER_VER = 0.3.1

.PHONY: format
format:
	black --include "bin" .
	black .

# pyment -w -o google --first-line false --ignore-private false network_importer

unit-tests:
	docker run -v $(shell pwd):/source $(DOCKER_IMAGE):$(DOCKER_VER)  pytest -v

start-batfish:
	docker run -d -p 9997:9997 -p 9996:9996 batfish/batfish 

tests: check-format unit-tests

.PHONY: build
build:
	docker build -t $(DOCKER_IMAGE):$(DOCKER_VER) .
  docker tag $(DOCKER_IMAGE):$(DOCKER_VER) $(DOCKER_IMAGE):latest

.PHONY: check-format
check-format:
	@echo "Starting  lint"
	docker run -v $(shell pwd):/source $(DOCKER_IMAGE):$(DOCKER_VER) black --check --include "bin" .
	docker run -v $(shell pwd):/source $(DOCKER_IMAGE):$(DOCKER_VER) black --check .
	docker run -v $(shell pwd):/source $(DOCKER_IMAGE):$(DOCKER_VER) make pylint
	docker run -v $(shell pwd):/source $(DOCKER_IMAGE):$(DOCKER_VER) bandit -r ./ -c .bandit
	@echo "Completed lint"

# Using to pass arguments to pylint that would fail in docker run command
.PHONY: pylint
pylint:
	find ./ -name "*.py" | xargs pylint
