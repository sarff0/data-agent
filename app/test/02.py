from dataclasses import dataclass
from pathlib import Path
from omegaconf import OmegaConf
# 定义封装实体
@dataclass
class AppConfig:
    name: str
    age: int
    height: float
    file: dict

# 定义配置路径
config_file = Path(__file__).parents[2] / 'conf' / 'text_config.yaml'
# 读取配置数据
content = OmegaConf.load(config_file)
# 创建封装结构
schema = OmegaConf.structured(AppConfig)
# 封装配置内容到配置对象中
app_config: AppConfig = OmegaConf.to_object(OmegaConf.merge(schema, content))
# 获取配置数据
print(app_config)