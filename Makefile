.ONESHELL:

.PHONY: help
help:             ## Show the help.
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@fgrep "##" Makefile | fgrep -v fgrep


.PHONY: show
show:             ## Show the current environment.
	@echo "Current environment:"
  @poetry env info

.PHONY: install
install:          ## Install the project in dev mode.
	poetry install --with development


.PHONY: fmt
fmt:              ## Format code using black & isort.
	@poetry run ruff format

.PHONY: lint
lint:             ## Run pep8, black, mypy linters.
	@poetry run ruff check

.PHONY: test
test: lint        ## Run tests and generate coverage report.
	@poetry run pytest -v -l --cov-config .coveragerc --cov-report lcov --cov=workflow --tb=short --maxfail=1 tests/
	@poetry run coverage xml
	@poetry run coverage html

.PHONY: watch
watch:            ## Run tests on every change.
	ls **/**.py | entr poetry run pytest --picked=first -s -vvv -l --tb=long --maxfail=1 tests/

.PHONY: clean
clean:            ## Clean unused files.
	@find ./ -name '*.pyc' -exec rm -f {} \;
	@find ./ -name '__pycache__' -exec rm -rf {} \;
	@find ./ -name 'Thumbs.db' -exec rm -f {} \;
	@find ./ -name '*~' -exec rm -f {} \;
	@rm -rf .cache
	@rm -rf .pytest_cache
	@rm -rf .mypy_cache
	@rm -rf build
	@rm -rf dist
	@rm -rf *.egg-info
	@rm -rf htmlcov
	@rm -rf .tox/
	@rm -rf docs/_build

.PHONY: virtualenv
virtualenv:       ## Create a virtual environment.
	@poetry env use python3
	@poetry install --with development

.PHONY: release
release:          ## Create a new tag for release.
	@echo "WARNING: This operation will create s version tag and push to github"
	@read -p "Version? (provide the next x.y.z semver) : " TAG
	@echo "creating git tag : $${TAG}"
	@git tag $${TAG}
	@echo "$${TAG}" > workflow/VERSION
	@$(ENV_PREFIX)gitchangelog > HISTORY.md
	@git add workflow/VERSION HISTORY.md
	@git commit -m "release: version $${TAG} 🚀"
	@git push -u origin HEAD --tags
	@echo "Github Actions will detect the new tag and release the new version."

# .PHONY: docs
# docs:             ## Build the documentation.
# 	@echo "building documentation ..."
# 	@$(ENV_PREFIX)mkdocs build
# 	URL="site/index.html"; xdg-open $$URL || sensible-browser $$URL || x-www-browser $$URL || gnome-open $$URL  || open $$URL

.PHONY: export-dependencies
export-dependencies: ## export deps to requirements.txt
	@poetry self add poetry-plugin-export
	@poetry export --output requirements.txt
	@poetry export --only=development --output requirements-test.txt 

.PHONY: shell
shell:            ## Open a shell in the project.
	@poetry shell

.PHONY: docker-build
docker-build:	  ## Builder docker images
	@docker-compose -f docker-compose-dev.yaml -p workflow build

.PHONY: docker-run
docker-run:  	  ## Run docker development images
	@docker-compose -f docker-compose-dev.yaml -p workflow up -d

.PHONY: docker-stop
docker-stop: 	  ## Bring down docker dev environment
	@docker-compose -f docker-compose-dev.yaml -p workflow down

.PHONY: docker-ps
docker-ps: 	  ## Bring down docker dev environment
	@docker-compose -f docker-compose-dev.yaml -p workflow ps

.PHONY: docker-log
docker-logs: 	  ## Bring down docker dev environment
	@docker-compose -f docker-compose-dev.yaml -p workflow logs -f app
