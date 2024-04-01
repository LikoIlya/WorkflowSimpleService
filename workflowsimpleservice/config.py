import os

from dynaconf import Dynaconf

HERE = os.path.dirname(os.path.abspath(__file__))

settings = Dynaconf(
    envvar_prefix="workflowsimpleservice",
    preload=[os.path.join(HERE, "default.toml")],
    settings_files=["settings.toml", ".secrets.toml"],
    environments=["development", "production", "testing"],
    env_switcher="workflowsimpleservice_env",
    load_dotenv=False,
)


"""
# How to use this application settings

```
from workflowsimpleservice.config import settings
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
export workflowsimpleservice_KEY=value
export workflowsimpleservice_KEY="@int 42"
export workflowsimpleservice_KEY="@jinja {{ this.db.uri }}"
export workflowsimpleservice_DB__uri="@jinja {{ this.db.uri | replace('db', 'data') }}"
```

### Switching environments
```
workflowsimpleservice_ENV=production workflowsimpleservice run
```

Read more on https://dynaconf.com
"""
