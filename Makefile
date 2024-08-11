.PHONY : test compile fmt demo
default: compile;

test:
	pytest --verbose .

compile:
	mypy --strict targurs.py test_targurs.py

demo:
	python demo.py
fmt:
	black .

all: fmt compile test demo
