import os
import logging
from typing import Dict, Any, Optional

from jinja2 import Environment, FileSystemLoader, TemplateError

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_prompt_template(template: str, **kwargs) -> str:
    """
    应用模板渲染功能
    
    Args:
        template: 模板文件名（不含.md扩展名）或完整的模板文件路径
        **kwargs: 传递给模板的变量
    
    Returns:
        渲染后的模板内容
    
    Raises:
        FileNotFoundError: 当模板文件不存在时
        TemplateError: 当模板渲染出错时
    """
    try:
        # 获取prompt目录作为模板目录
        prompt_dir = os.path.dirname(__file__)
        
        # 创建Jinja2环境
        env = Environment(
            loader=FileSystemLoader(prompt_dir),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # 确定模板文件名
        if template.endswith('.md'):
            template_name = os.path.basename(template)
        else:
            template_name = f"{template}.md"
        
        logger.info(f"加载模板: {template_name} 从目录: {prompt_dir}")
        
        # 获取并渲染模板
        template_obj = env.get_template(template_name)
        rendered_content = template_obj.render(**kwargs)
        
        logger.debug(f"模板渲染成功，输出长度: {len(rendered_content)} 字符")
        return rendered_content
        
    except TemplateError as e:
        logger.error(f"模板渲染错误: {str(e)}")
        raise
    except FileNotFoundError as e:
        logger.error(f"模板文件未找到: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"加载模板时发生未预期错误: {str(e)}")
        raise

def load_prompt_file(file_path: str) -> str:
    """
    直接加载提示文件内容（不进行模板渲染）
    
    Args:
        file_path: 提示文件的路径
    
    Returns:
        文件的原始内容
    
    Raises:
        FileNotFoundError: 当文件不存在时
        IOError: 当文件读取失败时
    """
    try:
        # 如果提供的是相对路径，相对于prompt目录解析
        if not os.path.isabs(file_path):
            prompt_dir = os.path.dirname(__file__)
            file_path = os.path.join(prompt_dir, file_path)
        
        logger.info(f"直接加载文件: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.debug(f"文件加载成功，长度: {len(content)} 字符")
        return content
        
    except Exception as e:
        logger.error(f"加载文件时出错: {str(e)}")
        raise

def get_project_root() -> str:
    """
    获取项目根目录路径
    
    Returns:
        项目根目录的绝对路径
    """
    # 从当前文件路径向上查找项目根目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 假设src目录是项目根目录下的一级目录
    project_root = os.path.dirname(current_dir) if os.path.basename(current_dir) == 'src' else current_dir
    
    logger.debug(f"检测到项目根目录: {project_root}")
    return project_root