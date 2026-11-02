from pathlib import Path

from omegaconf import OmegaConf
# 定义配置路径
config_file = Path(__file__).parents[2] / 'conf' / 'text_config.yaml'
# 读取配置数据
conf = OmegaConf.load(config_file)
# 获取配置内容
print(conf)