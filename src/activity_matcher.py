import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from database_manager import ActivityMetadata

logger = logging.getLogger(__name__)

@dataclass
class MatchResult:
    """匹配结果"""
    is_match: bool
    confidence: float  # 0.0 - 1.0
    reasons: List[str]

class ActivityMatcher:
    """活动匹配器，用于识别跨平台的重复活动"""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        
        # 匹配阈值配置
        self.thresholds = {
            'time_tolerance_minutes': 5,      # 时间容差（分钟）
            'distance_tolerance_percent': 5,   # 距离容差（百分比）
            'duration_tolerance_percent': 10,  # 时长容差（百分比）
            'min_confidence': 0.7             # 最小匹配置信度
        }
    
    def debug_print(self, message: str) -> None:
        """只在调试模式下打印信息"""
        if self.debug:
            print(f"[ActivityMatcher] {message}")
    
    def match_activities(self, activity1: ActivityMetadata, activity2: ActivityMetadata) -> MatchResult:
        """匹配两个活动是否为同一活动"""
        reasons = []
        confidence_factors = []
        
        # 1. 时间匹配检查
        time_match, time_confidence, time_reason = self._check_time_match(activity1, activity2)
        reasons.append(time_reason)
        confidence_factors.append(time_confidence)
        
        # 2. 运动类型匹配检查
        sport_match, sport_confidence, sport_reason = self._check_sport_type_match(activity1, activity2)
        reasons.append(sport_reason)
        confidence_factors.append(sport_confidence)
        
        # 3. 距离匹配检查
        distance_match, distance_confidence, distance_reason = self._check_distance_match(activity1, activity2)
        reasons.append(distance_reason)
        confidence_factors.append(distance_confidence)
        
        # 4. 时长匹配检查
        duration_match, duration_confidence, duration_reason = self._check_duration_match(activity1, activity2)
        reasons.append(duration_reason)
        confidence_factors.append(duration_confidence)
        
        # 计算总体置信度（加权平均）
        weights = [0.4, 0.2, 0.2, 0.2]  # 时间权重最高
        total_confidence = sum(c * w for c, w in zip(confidence_factors, weights))
        
        # 判断是否匹配
        is_match = (time_match and sport_match and 
                   total_confidence >= self.thresholds['min_confidence'])
        
        self.debug_print(f"活动匹配结果: {is_match}, 置信度: {total_confidence:.2f}")
        self.debug_print(f"匹配原因: {reasons}")
        
        return MatchResult(
            is_match=is_match,
            confidence=total_confidence,
            reasons=reasons
        )
    
    def _check_time_match(self, activity1: ActivityMetadata, activity2: ActivityMetadata) -> Tuple[bool, float, str]:
        """检查时间匹配"""
        try:
            time1 = datetime.fromisoformat(activity1.start_time.replace('Z', '+00:00'))
            time2 = datetime.fromisoformat(activity2.start_time.replace('Z', '+00:00'))
            
            time_diff = abs((time1 - time2).total_seconds())
            tolerance_seconds = self.thresholds['time_tolerance_minutes'] * 60
            
            if time_diff <= tolerance_seconds:
                confidence = max(0.0, 1.0 - (time_diff / tolerance_seconds))
                return True, confidence, f"时间匹配 (差异: {time_diff/60:.1f}分钟)"
            else:
                return False, 0.0, f"时间不匹配 (差异: {time_diff/60:.1f}分钟)"
                
        except Exception as e:
            self.debug_print(f"时间解析失败: {e}")
            return False, 0.0, "时间解析失败"
    
    def _check_sport_type_match(self, activity1: ActivityMetadata, activity2: ActivityMetadata) -> Tuple[bool, float, str]:
        """检查运动类型匹配"""
        sport1 = self._normalize_sport_type(activity1.sport_type)
        sport2 = self._normalize_sport_type(activity2.sport_type)
        
        if sport1 == sport2:
            return True, 1.0, f"运动类型匹配 ({sport1})"
        else:
            # 检查是否为相似的运动类型
            if self._are_similar_sports(sport1, sport2):
                return True, 0.8, f"运动类型相似 ({sport1} ≈ {sport2})"
            else:
                return False, 0.0, f"运动类型不匹配 ({sport1} vs {sport2})"
    
    def _check_distance_match(self, activity1: ActivityMetadata, activity2: ActivityMetadata) -> Tuple[bool, float, str]:
        """检查距离匹配"""
        if activity1.distance == 0 and activity2.distance == 0:
            return True, 1.0, "距离匹配 (都为0)"
        
        if activity1.distance == 0 or activity2.distance == 0:
            return True, 0.5, "距离部分匹配 (一个为0)"
        
        distance_diff = abs(activity1.distance - activity2.distance)
        avg_distance = (activity1.distance + activity2.distance) / 2
        diff_percent = (distance_diff / avg_distance) * 100
        
        tolerance_percent = self.thresholds['distance_tolerance_percent']
        
        if diff_percent <= tolerance_percent:
            confidence = max(0.0, 1.0 - (diff_percent / tolerance_percent))
            return True, confidence, f"距离匹配 (差异: {diff_percent:.1f}%)"
        else:
            return False, 0.0, f"距离不匹配 (差异: {diff_percent:.1f}%)"
    
    def _check_duration_match(self, activity1: ActivityMetadata, activity2: ActivityMetadata) -> Tuple[bool, float, str]:
        """检查时长匹配"""
        if activity1.duration == 0 and activity2.duration == 0:
            return True, 1.0, "时长匹配 (都为0)"
        
        if activity1.duration == 0 or activity2.duration == 0:
            return True, 0.5, "时长部分匹配 (一个为0)"
        
        duration_diff = abs(activity1.duration - activity2.duration)
        avg_duration = (activity1.duration + activity2.duration) / 2
        diff_percent = (duration_diff / avg_duration) * 100
        
        tolerance_percent = self.thresholds['duration_tolerance_percent']
        
        if diff_percent <= tolerance_percent:
            confidence = max(0.0, 1.0 - (diff_percent / tolerance_percent))
            return True, confidence, f"时长匹配 (差异: {diff_percent:.1f}%)"
        else:
            return False, 0.0, f"时长不匹配 (差异: {diff_percent:.1f}%)"
    
    def _normalize_sport_type(self, sport_type: str) -> str:
        """标准化运动类型"""
        sport_mapping = {
            # 跑步相关
            'run': 'running',
            'running': 'running',
            'trail_run': 'running',
            'treadmill_running': 'running',
            
            # 骑行相关
            'ride': 'cycling',
            'cycling': 'cycling',
            'virtual_ride': 'cycling',
            'e_bike_ride': 'cycling',
            'mountain_bike_ride': 'cycling',
            'road_bike_ride': 'cycling',
            
            # 游泳相关
            'swim': 'swimming',
            'swimming': 'swimming',
            'open_water_swimming': 'swimming',
            'pool_swimming': 'swimming',
            
            # 步行相关
            'walk': 'walking',
            'walking': 'walking',
            'hike': 'walking',
            'hiking': 'walking',
        }
        
        normalized = sport_type.lower().replace(' ', '_')
        return sport_mapping.get(normalized, normalized)
    
    def _are_similar_sports(self, sport1: str, sport2: str) -> bool:
        """检查两个运动类型是否相似"""
        similar_groups = [
            {'running', 'trail_running', 'treadmill_running'},
            {'cycling', 'mountain_biking', 'road_cycling', 'virtual_cycling'},
            {'swimming', 'open_water_swimming', 'pool_swimming'},
            {'walking', 'hiking'},
        ]
        
        for group in similar_groups:
            if sport1 in group and sport2 in group:
                return True
        
        return False
    
    def find_matching_activities(self, target_activity: ActivityMetadata, 
                               candidate_activities: List[Tuple[str, ActivityMetadata]]) -> List[Tuple[str, MatchResult]]:
        """在候选活动中查找匹配的活动"""
        matches = []
        
        for activity_id, candidate in candidate_activities:
            match_result = self.match_activities(target_activity, candidate)
            if match_result.is_match:
                matches.append((activity_id, match_result))
        
        # 按置信度排序
        matches.sort(key=lambda x: x[1].confidence, reverse=True)
        
        self.debug_print(f"找到{len(matches)}个匹配的活动")
        return matches
    
    def get_best_match(self, target_activity: ActivityMetadata, 
                      candidate_activities: List[Tuple[str, ActivityMetadata]]) -> Optional[Tuple[str, MatchResult]]:
        """获取最佳匹配的活动"""
        matches = self.find_matching_activities(target_activity, candidate_activities)
        
        if matches:
            best_match = matches[0]
            self.debug_print(f"最佳匹配: ID={best_match[0]}, 置信度={best_match[1].confidence:.2f}")
            return best_match
        
        return None
    
    def set_threshold(self, key: str, value: float) -> None:
        """设置匹配阈值"""
        if key in self.thresholds:
            self.thresholds[key] = value
            self.debug_print(f"设置阈值 {key} = {value}")
        else:
            raise ValueError(f"未知的阈值参数: {key}")
    
    def get_thresholds(self) -> Dict[str, float]:
        """获取当前阈值配置"""
        return self.thresholds.copy() 