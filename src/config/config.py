import os
import yaml

__local_config = None

def load_config():
    global __local_config
    if __local_config is None:
        if not os.path.exists('config.yaml'):
            raise FileNotFoundError('config.yaml not found')
        with open('config.yaml', "r") as f:
            __local_config = yaml.safe_load(f)
    return __local_config

def get_config_section(key: str | list[str]) -> dict | None:
    global __local_config
    section = __local_config
    path = []
    if isinstance(key, str):
        path.append(key)
    else:
        path.extend(key)
    for key in path:
        if section is None or key not in section:
            return None
        section = section[key]
    return section

load_config()