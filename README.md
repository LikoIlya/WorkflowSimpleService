
---
# Workflow Service

[![codecov](https://codecov.io/gh/LikoIlya/WorkflowSimpleService/branch/main/graph/badge.svg?token=WorkflowSimpleService_token_here)](https://codecov.io/gh/LikoIlya/WorkflowSimpleService)
[![CI](https://github.com/LikoIlya/WorkflowSimpleService/actions/workflows/main.yml/badge.svg)](https://github.com/LikoIlya/WorkflowSimpleService/actions/workflows/main.yml)

Awesome "Workflow service" created by LikoIlya

## Install

from source
```bash
git clone https://github.com/LikoIlya/WorkflowSimpleService workflow
cd workflow
make install
make shell
```

from pypi (**UNRELEASED YET**)

```bash
pip install workflow
```

## Executing

```bash
$ poetry run workflow --port 8080
```

```bash
$ workflow run --port 8080
```

or

```bash
python -m workflow run --port 8080
```

or

```bash
$ uvicorn workflow:app
```

## CLI

```bash
❯ workflow --help
Usage: workflow [OPTIONS] COMMAND [ARGS]...

Options:
  --install-completion [bash|zsh|fish|powershell|pwsh]
                                  Install completion for the specified shell.
  --show-completion [bash|zsh|fish|powershell|pwsh]
                                  Show completion for the specified shell, to
                                  copy it or customize the installation.
  --help                          Show this message and exit.

Commands:
  run          Run the API server.
```

## API

Run with `workflow run` and access http://127.0.0.1:8000/docs

## Testing

``` bash
❯ make test
///////////////////
///Linting Stuff///
///////////////////
================================ test session starts ===========================
platform linux -- Python 3.9.6, pytest-6.2.5, py-1.10.0, pluggy-1.0.0 -- 
///////////////////
///  Test info  ///
///////////////////                                                                                                                       

tests/test_app.py::test_using_testing_db PASSED                           [ 10%]
tests/test_app.py::test_index PASSED                                      [ 20%]
....
tests/test_workflow_api.py PASSED                                         [100%]

----------- coverage: platform linux, python 3.9.6-final-0 -----------
///////////////////
///Coverage info///
///////////////////  

========================== N passed in 2.34s ==================================

```

## Linting and Formatting

```bash
make lint  # checks for linting errors
make fmt   # formats the code
```


## Configuration

This project uses [Dynaconf](https://dynaconf.com) to manage configuration.

```py
from workflow.config import settings
```

## Acessing variables

```py
settings.get("SECRET_KEY", default="sdnfjbnfsdf")
settings["SECRET_KEY"]
settings.SECRET_KEY
settings.db.uri
settings["db"]["uri"]
settings["db.uri"]
settings.DB__uri
```

## Defining variables

### On files

settings.toml

```toml
[development]
dynaconf_merge = true

[development.db]
echo = true
```

> `dynaconf_merge` is a boolean that tells if the settings should be merged with the default settings defined in workflow/default.toml.

### As environment variables
```bash
export workflow_KEY=value
export workflow_KEY="@int 42"
export workflow_KEY="@jinja {{ this.db.uri }}"
export workflow_DB__uri="@jinja {{ this.db.uri | replace('db', 'data') }}"
```

### Secrets

There is a file `.secrets.toml` where your sensitive variables are stored,
that file must be ignored by git. (add that to .gitignore)

Or store your secrets in environment variables or a vault service, Dynaconf
can read those variables.

### Switching environments

```bash
workflow_ENV=production workflow run
```

Read more on https://dynaconf.com

## Development

Read the [CONTRIBUTING.md](CONTRIBUTING.md) file.
