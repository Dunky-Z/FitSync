import os
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime
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
            '<gpx version="1.1" creator="FitSync" xmlns="http://www.topografix.com/GPX/1/1">'
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
    
    @staticmethod
    def analyze_fit_file(file_path: str) -> Dict:
        """
        分析FIT文件内容
        
        Args:
            file_path: FIT文件路径
            
        Returns:
            包含文件分析信息的字典
        """
        try:
            import fitdecode
            
            analysis = {
                'total_records': 0,
                'duration_seconds': 0,
                'total_distance_meters': 0,
                'has_heart_rate': False,
                'has_power': False,
                'has_cadence': False,
                'has_gps': False
            }
            
            # 简单的FIT文件分析
            with fitdecode.FitReader(file_path) as fit_reader:
                records = []
                for frame in fit_reader:
                    if isinstance(frame, fitdecode.FitDataMessage):
                        if frame.name == 'record':
                            records.append(frame)
                            # 检查数据类型
                            for field in frame.fields:
                                if field.name == 'heart_rate' and field.value is not None:
                                    analysis['has_heart_rate'] = True
                                elif field.name == 'power' and field.value is not None:
                                    analysis['has_power'] = True
                                elif field.name == 'cadence' and field.value is not None:
                                    analysis['has_cadence'] = True
                                elif field.name in ['position_lat', 'position_long'] and field.value is not None:
                                    analysis['has_gps'] = True
                
                analysis['total_records'] = len(records)
                
                if records:
                    # 计算时长
                    start_time = None
                    end_time = None
                    total_distance = 0
                    
                    for record in records:
                        for field in record.fields:
                            if field.name == 'timestamp' and field.value is not None:
                                if start_time is None:
                                    start_time = field.value
                                end_time = field.value
                            elif field.name == 'distance' and field.value is not None:
                                total_distance = field.value
                    
                    if start_time and end_time:
                        analysis['duration_seconds'] = (end_time - start_time).total_seconds()
                    
                    analysis['total_distance_meters'] = total_distance
            
            logger.info(f"FIT文件分析完成: {analysis}")
            return analysis
            
        except ImportError:
            logger.warning("缺少fitdecode库，无法分析FIT文件")
            return {}
        except Exception as e:
            logger.error(f"分析FIT文件失败: {e}")
            return {}
    
    @staticmethod
    def convert_fit_to_gpx(fit_file_path: str, output_path: Optional[str] = None, 
                          include_metadata: bool = True) -> Optional[str]:
        """
        将FIT文件转换为GPX格式
        
        Args:
            fit_file_path: FIT文件路径
            output_path: 输出GPX文件路径（可选，默认与原文件同目录）
            include_metadata: 是否包含活动元数据
        
        Returns:
            转换后的GPX文件路径，失败时返回None
        """
        try:
            from fit2gpx import Converter
            
            # 验证输入文件
            if not os.path.exists(fit_file_path):
                raise ValueError(f"FIT文件不存在: {fit_file_path}")
            
            # 确定输出路径
            if output_path is None:
                base_name = os.path.splitext(fit_file_path)[0]
                output_path = f"{base_name}.gpx"
            
            logger.info(f"开始转换FIT文件: {fit_file_path} -> {output_path}")
            
            # 创建转换器
            conv = Converter()
            
            # 执行转换
            gpx = conv.fit_to_gpx(f_in=fit_file_path, f_out=output_path)
            
            if os.path.exists(output_path):
                logger.info(f"FIT转GPX完成: {output_path}")
                return output_path
            else:
                logger.error("转换完成但输出文件不存在")
                return None
            
        except ImportError as e:
            logger.error(f"缺少fit2gpx库: {e}")
            logger.error("请安装: pip install fit2gpx")
            return None
        except Exception as e:
            logger.error(f"FIT转GPX失败: {e}")
            return None 