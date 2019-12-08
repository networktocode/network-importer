
format:
	black --include "bin" .
	black .

start-batfish:
	docker run -d -p 9997:9997 -p 9996:9996 batfish/batfish 