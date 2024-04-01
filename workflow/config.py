import os

from dynaconf import Dynaconf

HERE = os.path.dirname(os.path.abspath(__file__))

settings = Dynaconf(
<<<<<<<< HEAD:workflowsimpleservice/config.py
    envvar_prefix="workflowsimpleservice",
    preload=[os.path.join(HERE, "default.toml")],
    settings_files=["settings.toml", ".secrets.toml"],
    environments=["development", "production", "testing"],
    env_switcher="workflowsimpleservice_env",
========
    envvar_prefix="workflow",
    preload=[os.path.join(HERE, "default.toml")],
    settings_files=["settings.toml", ".secrets.toml"],
    environments=["development", "production", "testing"],
    env_switcher="workflow_env",
>>>>>>>> cac4d36 (✅ Ready to clone and code.):workflow/config.py
    load_dotenv=False,
)


"""
# How to use this application settings

```
<<<<<<<< HEAD:workflowsimpleservice/config.py
from workflowsimpleservice.config import settings
========
from workflow.config import settings
>>>>>>>> cac4d36 (✅ Ready to clone and code.):workflow/config.py
```

## Acessing variables

```
settings.get("SECRET_KEY", default="sdnfjbnfsdf")
settings["SECRET_KEY"]
settings.SECRET_KEY
settings.db.uri
settings["db"]["uri"]
settings["db.uri"]
settings.DB__uri
```

## Modifying variables

### On files

settings.toml
```
[development]
KEY=value
```

### As environment variables
```
<<<<<<<< HEAD:workflowsimpleservice/config.py
export workflowsimpleservice_KEY=value
export workflowsimpleservice_KEY="@int 42"
export workflowsimpleservice_KEY="@jinja {{ this.db.uri }}"
export workflowsimpleservice_DB__uri="@jinja {{ this.db.uri | replace('db', 'data') }}"
========
export workflow_KEY=value
export workflow_KEY="@int 42"
export workflow_KEY="@jinja {{ this.db.uri }}"
export workflow_DB__uri="@jinja {{ this.db.uri | replace('db', 'data') }}"
>>>>>>>> cac4d36 (✅ Ready to clone and code.):workflow/config.py
```

### Switching environments
```
<<<<<<<< HEAD:workflowsimpleservice/config.py
workflowsimpleservice_ENV=production workflowsimpleservice run
========
workflow_ENV=production workflow run
>>>>>>>> cac4d36 (✅ Ready to clone and code.):workflow/config.py
```

Read more on https://dynaconf.com
"""
