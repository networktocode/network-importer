
DOCKER_IMAGE = networktocode/network-importer
DOCKER_VER = 0.5.0dev

format:
	black .

# pyment -w -o google --first-line false --ignore-private false network_importer

.PHONY: unit-tests
unit-tests:
	docker run -v $(shell pwd):/source -w /source $(DOCKER_IMAGE):$(DOCKER_VER)  pytest -v

.PHONY: start-batfish
start-batfish:
	docker run -d -p 9997:9997 -p 9996:9996 batfish/batfish 

.PHONY: tests
tests: check-format unit-tests

.PHONY: build
build:
	docker build -t $(DOCKER_IMAGE):$(DOCKER_VER) .
	docker tag $(DOCKER_IMAGE):$(DOCKER_VER) $(DOCKER_IMAGE):latest

.PHONY: import
import:
	@echo "Starting Network-Importer"
	@docker run -it \
		--env-file .env \
		-v $(shell pwd)/network_importer:/source/network_importer \
		-v $(shell pwd)/examples:/source/examples \
		-v $(shell pwd)/tests:/source/tests \
		$(DOCKER_IMAGE):$(DOCKER_VER) network-importer $(NI_OPTS) 
	@echo "Network-Importer complete"
	@echo "Restarting Batfish to release memory ..."
	@docker restart batfish

.PHONY: dev
dev:
	docker run -it \
		-v $(shell pwd)/network_importer:/source/network_importer \
		-v $(shell pwd)/examples:/source/examples \
		-v $(shell pwd)/tests:/source/tests \
		$(DOCKER_IMAGE):$(DOCKER_VER) bash

.PHONY: check-format
check-format:
	@echo "Starting  lint"
	docker run -v $(shell pwd):/source -w /source $(DOCKER_IMAGE):$(DOCKER_VER) black --check .
	docker run -v $(shell pwd):/source -w /source $(DOCKER_IMAGE):$(DOCKER_VER) make pylint
	docker run -v $(shell pwd):/source -w /source $(DOCKER_IMAGE):$(DOCKER_VER) bandit --recursive --config .bandit.yml .
	@echo "Completed lint"

# Using to pass arguments to pylint that would fail in docker run command
.PHONY: pylint
pylint:
	find ./ -name "*.py" | xargs pylint
