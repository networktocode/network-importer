
format:
	black --include "bin" .
	black .

check-format:
	black --check --include "bin" .
	black --check .

unit-tests:
	pytest -v .

start-batfish:
	docker run -d -p 9997:9997 -p 9996:9996 batfish/batfish 

tests: check-format