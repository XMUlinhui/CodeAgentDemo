import os
import yaml

__local_config = None

def load_config():
    global __local_config
    if __local_config is None:
        # 使用绝对路径查找配置文件，先在当前目录查找，再在项目根目录查找
        config_paths = ['config.yaml', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config.yaml')]
        config_file = None
        
        for path in config_paths:
            if os.path.exists(path):
                config_file = path
                break
        
        if config_file is None:
            raise FileNotFoundError('config.yaml not found in any expected location')
        
        # 明确使用UTF-8编码打开文件，避免在Windows上使用默认的gbk编码
        with open(config_file, "r", encoding="utf-8") as f:
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