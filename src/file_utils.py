import os
import logging
from typing import Optional
from defusedxml.minidom import parseString
from tcxreader.tcxreader import TCXReader

logger = logging.getLogger(__name__)

class FileUtils:
    """文件处理工具类"""
    
    @staticmethod
    def sanitize_filename(name: str) -> str:
        """清理文件名，移除不合法字符"""
        # 移除或替换不合法的文件名字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        
        # 移除前后空格
        name = name.strip()
        
        # 限制长度
        if len(name) > 100:
            name = name[:100]
        
        # 如果为空，使用默认名称
        if not name:
            name = "activity"
        
        return name
    
    @staticmethod
    def validate_file(file_path: str) -> None:
        """验证文件格式"""
        if not os.path.exists(file_path):
            raise ValueError(f"文件不存在: {file_path}")
        
        if file_path.endswith('.fit'):
            FileUtils._validate_fit_file(file_path)
        else:
            FileUtils._validate_xml_file(file_path)
    
    @staticmethod
    def _validate_fit_file(file_path: str) -> None:
        """验证FIT文件"""
        try:
            file_size = os.path.getsize(file_path)
            
            if file_size == 0:
                raise ValueError("FIT文件为空")
            
            # 简单的FIT文件头验证
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if len(header) < 4:
                    raise ValueError("无效的FIT文件头")
            
            logger.info("FIT文件验证通过")
            
        except Exception as e:
            logger.error(f"FIT文件验证失败: {e}")
            raise ValueError(f"FIT文件验证失败: {e}")
    
    @staticmethod
    def _validate_xml_file(file_path: str) -> None:
        """验证XML文件"""
        with open(file_path, "r", encoding='utf-8') as file:
            content = file.read()
        
        if not content:
            raise ValueError("文件为空")
        
        if '<?xml' not in content:
            raise ValueError("无效的XML文件格式")
        
        logger.info("XML文件验证通过")
    
    @staticmethod
    def convert_to_gpx(file_path: str) -> str:
        """将TCX文件转换为GPX格式（如果需要）"""
        if file_path.endswith('.gpx'):
            return file_path
        
        # 如果是TCX文件，读取并转换为GPX格式
        if file_path.endswith('.tcx'):
            try:
                tcx_reader = TCXReader()
                data = tcx_reader.read(file_path)
                
                # 创建GPX文件路径
                gpx_path = file_path.replace('.tcx', '.gpx')
                
                # 简单的TCX到GPX转换
                FileUtils._convert_tcx_to_gpx(file_path, gpx_path)
                
                logger.info(f"TCX转换为GPX: {gpx_path}")
                return gpx_path
            except Exception as e:
                logger.warning(f"TCX转换失败，使用原文件: {e}")
                return file_path
        
        return file_path
    
    @staticmethod
    def _convert_tcx_to_gpx(tcx_path: str, gpx_path: str) -> None:
        """简单的TCX到GPX转换"""
        with open(tcx_path, 'r', encoding='utf-8') as f:
            tcx_content = f.read()
        
        # 基本的格式转换（简化版）
        gpx_content = tcx_content.replace(
            '<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">',
            '<gpx version="1.1" creator="Strava-to-MultiPlatform" xmlns="http://www.topografix.com/GPX/1/1">'
        )
        gpx_content = gpx_content.replace('</TrainingCenterDatabase>', '</gpx>')
        
        with open(gpx_path, 'w', encoding='utf-8') as f:
            f.write(gpx_content)
    
    @staticmethod
    def indent_xml_file(file_path: str) -> None:
        """格式化XML文件"""
        try:
            with open(file_path, "r", encoding='utf-8') as xml_file:
                xml_content = xml_file.read()

            xml_dom = parseString(xml_content)

            with open(file_path, "w", encoding='utf-8') as xml_file:
                xml_file.write(xml_dom.toprettyxml(indent="  "))
        except Exception:
            logger.warning("XML文件格式化失败，文件将以原格式保存")
    
    @staticmethod
    def get_latest_download() -> Optional[str]:
        """获取最新下载的活动文件"""
        download_folder = os.path.expanduser("~/Downloads")
        try:
            files = os.listdir(download_folder)
        except FileNotFoundError:
            logger.warning("未找到Downloads文件夹")
            return None
        
        # 查找活动文件
        activity_files = [f for f in files if f.endswith(('.tcx', '.gpx', '.fit'))]
        paths = [os.path.join(download_folder, f) for f in activity_files]

        if paths:
            latest_file = max(paths, key=os.path.getmtime)
            return latest_file
        else:
            logger.warning("在Downloads文件夹中未找到活动文件")
            return None
    
    @staticmethod
    def check_existing_activity_file(activity_id: str, activity_name: Optional[str] = None) -> Optional[str]:
        """检查Downloads文件夹中是否已存在相同活动ID的文件"""
        download_folder = os.path.expanduser("~/Downloads")
        
        try:
            files = os.listdir(download_folder)
        except FileNotFoundError:
            return None
        
        # 查找匹配的活动文件，支持更多格式
        for file in files:
            # 检查新的命名格式（使用活动名）和旧的命名格式
            if (f"_{activity_id}." in file and file.endswith(('.tcx', '.gpx', '.fit'))) or \
               (f"activity_{activity_id}" in file and file.endswith(('.tcx', '.gpx', '.fit'))):
                full_path = os.path.join(download_folder, file)
                # 验证文件是否有效
                try:
                    if file.endswith('.fit'):
                        # FIT文件是二进制格式，检查文件大小
                        if os.path.getsize(full_path) > 0:
                            return full_path
                    else:
                        # XML格式文件
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if content and '<?xml' in content:
                                return full_path
                except Exception:
                    continue
        
        return None 