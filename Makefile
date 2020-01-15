
DOCKER_IMAGE = networktocode/network-importer
DOCKER_VER = 0.1.2-dev

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