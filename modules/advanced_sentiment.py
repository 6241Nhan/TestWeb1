import re
from collections import Counter

class AdvancedSentimentAnalyzer:
    def __init__(self):
        self.sentiment_analyzer = None
        self.emotion_classifier = None
        
        # Không load model AI trên production để tránh lỗi
        # Chỉ sử dụng phân tích đơn giản
        print("Using simple sentiment analysis for production")
    
    def analyze_user_state(self, user_message):
        """Phân tích cảm xúc và trạng thái người dùng - Production version"""
        return self._simple_analysis(user_message)
    
    def _simple_analysis(self, text):
        """Phân tích đơn giản khi không có model"""
        text_lower = text.lower()
        
        # Basic sentiment detection
        positive_words = ['vui', 'tốt', 'tuyệt', 'thích', 'happy', 'good', 'cám ơn', 'thanks']
        negative_words = ['buồn', 'tệ', 'xấu', 'ghét', 'sad', 'bad', 'huhu', 'tiếc', 'không thích']
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = "positive"
        elif negative_count > positive_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"
            
        return {
            'sentiment': sentiment,
            'sentiment_score': 0.8,
            'emotion': self._detect_emotion_simple(text_lower),
            'emotion_score': 0.7,
            'urgency': self._detect_urgency(text_lower),
            'needs': self._extract_needs(text_lower),
            'special_scenario': self._detect_special_scenario(text_lower)
        }
    
    def _detect_emotion_simple(self, text_lower):
        """Phát hiện cảm xúc đơn giản"""
        emotion_keywords = {
            'sadness': ['buồn', 'huhu', 'khóc', 'thất vọng', 'chia tay', 'mất'],
            'joy': ['vui', 'happy', 'phấn khích', 'tuyệt vời', 'thích'],
            'anger': ['tức', 'giận', 'bực', 'khó chịu', 'tức giận'],
            'fear': ['sợ', 'lo', 'hoảng', 'bất an', 'lo lắng'],
            'surprise': ['ôi', 'wow', 'bất ngờ', 'ngạc nhiên']
        }
        
        for emotion, keywords in emotion_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return emotion
        return 'neutral'
    
    def _detect_urgency(self, text):
        """Phát hiện mức độ khẩn cấp"""
        text_lower = text.lower()
        urgency_keywords = {
            'high': ['gấp', 'ngay', 'khẩn cấp', 'cần ngay', 'nhanh', 'lập tức'],
            'medium': ['sớm', 'tuần sau', 'tháng sau', 'kế hoạch', 'dự định'],
            'low': ['lúc nào cũng được', 'không vội', 'tương lai', 'khi nào rảnh']
        }
        
        for level, keywords in urgency_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return level
        return 'medium'
    
    def _extract_needs(self, text):
        """Trích xuất nhu cầu ẩn"""
        text_lower = text.lower()
        needs = []
        
        need_patterns = {
            'relaxation': ['thư giãn', 'nghỉ ngơi', 'xả stress', 'mệt mỏi', 'căng thẳng'],
            'celebration': ['kỷ niệm', 'sinh nhật', 'cưới', 'thành công', 'ăn mừng'],
            'business': ['công tác', 'meeting', 'đối tác', 'dự án', 'work'],
            'adventure': ['khám phá', 'trải nghiệm', 'mạo hiểm', 'mới lạ', 'phiêu lưu'],
            'healing': ['chữa lành', 'tĩnh tâm', 'thiền', 'suy nghĩ', 'chia tay'],
            'family': ['gia đình', 'con nhỏ', 'trẻ em', 'bố mẹ', 'ông bà'],
            'romance': ['lãng mạn', 'người yêu', 'cặp đôi', 'tình nhân', 'anniversary']
        }
        
        for need, patterns in need_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                needs.append(need)
                
        return needs if needs else ['general_travel']
    
    def _detect_special_scenario(self, text):
        """Phát hiện các tình huống đặc biệt cần xử lý"""
        text_lower = text.lower()
        
        special_scenarios = {
            'room_unavailable': ['hết phòng', 'hết chỗ', 'full phòng', 'đầy phòng', 'không còn phòng', 'mất tiu'],
            'price_concern': ['đắt quá', 'mắc quá', 'giá cao', 'over budget', 'đắt đỏ'],
            'quality_concern': ['sạch không', 'vệ sinh', 'bẩn', 'dơ', 'đảm bảo', 'cam kết'],
            'safety_concern': ['an toàn không', 'có an ninh', 'nguy hiểm', 'safe', 'security'],
            'urgent_booking': ['gấp lắm', 'ngay bây giờ', 'khẩn cấp', 'cần ngay', 'lập tức']
        }
        
        for scenario, keywords in special_scenarios.items():
            if any(keyword in text_lower for keyword in keywords):
                return scenario
        
        return None
    
    def analyze_quality_concerns(self, user_message):
        """Phân tích các lo lắng về chất lượng dịch vụ"""
        text_lower = user_message.lower()
        
        quality_concerns = {
            'cleanliness': {
                'keywords': ['sạch không', 'vệ sinh', 'bẩn', 'dơ', 'clean', 'hygiene'],
                'focus': 'housekeeping_standards',
                'urgency': 'medium'
            },
            'safety': {
                'keywords': ['an toàn không', 'có an ninh', 'nguy hiểm', 'safe', 'security'],
                'focus': 'safety_measures', 
                'urgency': 'high'
            },
            'service_quality': {
                'keywords': ['nhân viên tốt không', 'dịch vụ', 'phục vụ', 'service', 'staff'],
                'focus': 'service_standards',
                'urgency': 'medium'
            },
            'facility_condition': {
                'keywords': ['hồ bơi sạch', 'phòng cũ', 'thiết bị', 'facility', 'condition'],
                'focus': 'maintenance',
                'urgency': 'medium'
            },
            'direct_guarantee': {
                'keywords': ['có đảm bảo không', 'bạn đảm bảo', 'cam kết', 'chắc chắn không'],
                'focus': 'accountability',
                'urgency': 'high'
            }
        }
        
        for concern, data in quality_concerns.items():
            if any(keyword in text_lower for keyword in data['keywords']):
                return concern, data
        
        return None, None

