import numpy as np
import pandas as pd
from collections import Counter

class ContextAwareRecommender:
    def __init__(self):
        self.sentence_model = None  # Không dùng model trên production
        
        # Context embeddings đơn giản
        self.context_embeddings = self._initialize_context_embeddings()
        
    def _initialize_context_embeddings(self):
        """Khởi tạo embeddings đơn giản cho các ngữ cảnh du lịch"""
        contexts = {
            'heartbreak_recovery': "buồn tình cảm chia tay healing tâm hồn thất tình cô đơn",
            'business_trip': "công tác chuyên nghiệp hiệu quả meeting đối tác work",
            'family_vacation': "gia đình trẻ em an toàn vui chơi trẻ nhỏ", 
            'romantic_getaway': "lãng mạn cặp đôi riêng tư đặc biệt tình nhân",
            'solo_adventure': "một mình khám phá tự do trải nghiệm cá nhân",
            'stress_relief': "căng thẳng nghỉ ngơi thư giãn trị liệu mệt mỏi",
            'celebration': "kỷ niệm ăn mừng party vui vẻ thành công",
            'workation': "làm việc từ xa digital nomad wifi yên tĩnh"
        }
        return contexts
    
    def predict_travel_context(self, user_message, user_history=None):
        """Dự đoán ngữ cảnh du lịch - Production version"""
        return self._simple_context_prediction(user_message)
    
    def _simple_context_prediction(self, user_message):
        """Dự đoán ngữ cảnh đơn giản"""
        text_lower = user_message.lower()
        
        context_keywords = {
            'heartbreak_recovery': ['chia tay', 'buồn', 'thất tình', 'cô đơn', 'tình cảm'],
            'business_trip': ['công tác', 'meeting', 'đối tác', 'work', 'business'],
            'family_vacation': ['gia đình', 'con nhỏ', 'trẻ em', 'bố mẹ'],
            'romantic_getaway': ['lãng mạn', 'người yêu', 'cặp đôi', 'tình nhân'],
            'solo_adventure': ['một mình', 'solo', 'đi riêng', 'cá nhân'],
            'workation': ['làm việc', 'wifi', 'yên tĩnh', 'remote work']
        }
        
        scores = {context: 0 for context in context_keywords.keys()}
        
        for context, keywords in context_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    scores[context] += 1
        
        if max(scores.values()) > 0:
            primary_context = max(scores.items(), key=lambda x: x[1])[0]
            return {
                'primary_context': primary_context,
                'secondary_context': None,
                'confidence_scores': scores
            }
        else:
            return {
                'primary_context': 'general_travel',
                'secondary_context': None,
                'confidence_scores': scores
            }
    
    def generate_context_specific_suggestions(self, user_context, hotels_df):
        """Tạo đề xuất dựa trên ngữ cảnh"""
        context_recommendations = {
            'heartbreak_recovery': {
                'priority_features': ['spa', 'sea_view', 'quiet', 'nature', 'view'],
                'avoid_features': ['party', 'noisy', 'family_heavy'],
                'message_tone': 'empathetic_healing',
                'hotel_types': ['resort', 'boutique', 'wellness']
            },
            'business_trip': {
                'priority_features': ['wifi', 'conference', 'city_center', 'business_center'],
                'avoid_features': ['remote', 'no_internet', 'party'],
                'message_tone': 'professional_practical', 
                'hotel_types': ['business', 'luxury', 'boutique']
            },
            'workation': {
                'priority_features': ['wifi', 'quiet', 'workspace', 'city_center'],
                'avoid_features': ['noisy', 'party', 'family_heavy'],
                'message_tone': 'productive_focused',
                'hotel_types': ['business', 'boutique', 'apartment']
            },
            'general_travel': {
                'priority_features': ['rating', 'value', 'location'],
                'avoid_features': [],
                'message_tone': 'friendly_helpful',
                'hotel_types': ['all']
            }
        }
        
        context_rules = context_recommendations.get(
            user_context['primary_context'], 
            context_recommendations['general_travel']
        )
        
        return context_rules

