.PHONY: clean clean-test clean-pyc clean-build docs help
.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys

try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python -c "$$BROWSER_PYSCRIPT"

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .pytest_cache/
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

lint: ## reformat with black and check style with flake8
	isort -rc fastapi_permissions
	isort -rc tests
	black fastapi_permissions tests
	flake8 fastapi_permissions tests

test: ## run tests quickly with the default Python
	pytest tests -x --disable-warnings -k "not app"

coverage: ## full test suite, check code coverage and open coverage report
	pytest tests --cov=fastapi_permissions
	coverage html
	$(BROWSER) htmlcov/index.html

tox:  ## run fully isolated tests with tox
	tox

install:  ## install updated project.toml with flint
	flit install --pth-file

devenv: ## setup development environment
	python3 -m venv --prompt permissions .venv
	.venv/bin/pip3 install --upgrade pip
	.venv/bin/pip3 install flit
	.venv/bin/flit install --pth-file

repo: devenv ## complete project setup with development environment and git repo
	git init .
	.venv/bin/pre-commit install
	git add .
	git commit -m "import of project template" --no-verify
