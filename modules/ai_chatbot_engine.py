# modules/ai_chatbot_engine.py
from datetime import datetime

class AIChatbotEngine:
    def __init__(self):
        from modules.advanced_sentiment import AdvancedSentimentAnalyzer
        from modules.context_aware_recommender import ContextAwareRecommender
        from modules.personality_analyzer import PersonalityAnalyzer
        
        self.sentiment_analyzer = AdvancedSentimentAnalyzer()
        self.context_recommender = ContextAwareRecommender()
        self.personality_analyzer = PersonalityAnalyzer()
        self.conversation_memory = {}
    
    def process_user_message(self, user_id, message, conversation_history=None):
        """Xử lý tin nhắn với AI nâng cao"""
        # Phân tích đa chiều
        sentiment_analysis = self.sentiment_analyzer.analyze_user_state(message)
        context_prediction = self.context_recommender.predict_travel_context(message)
        personality_profile = self.personality_analyzer.analyze_personality_from_text(message)
        
        # Tổng hợp insights
        user_insights = {
            'sentiment': sentiment_analysis,
            'context': context_prediction,
            'personality': personality_profile,
            'timestamp': datetime.now(),
            'special_scenario': sentiment_analysis.get('special_scenario')
        }
        
        # Lưu vào memory
        if user_id not in self.conversation_memory:
            self.conversation_memory[user_id] = []
        self.conversation_memory[user_id].append(user_insights)
        
        # Tạo phản hồi thông minh
        response = self._generate_ai_response(user_insights, message)
        
        return {
            'response': response,
            'insights': user_insights,
            'recommendation_strategy': self._get_recommendation_strategy(user_insights)
        }
    
    def _generate_ai_response(self, insights, original_message):
        """Tạo phản hồi AI thông minh"""
        sentiment = insights['sentiment']['sentiment']
        emotion = insights['sentiment']['emotion']
        primary_context = insights['context']['primary_context']
        
        # Emotional response mapping
        emotional_responses = {
            'sadness': "Mình thấy bạn đang có chút buồn. Đôi khi một chuyến đi nhỏ có thể giúp tâm trạng tốt hơn đấy 💫",
            'joy': "Tuyệt vời! Niềm vui của bạn làm mình cũng thấy phấn khích 🎉",
            'anger': "Mình hiểu cảm giác bức bối này. Một không gian yên tĩnh có thể giúp bạn lấy lại cân bằng 🌿",
            'fear': "Đừng lo lắng quá, mình sẽ giúp bạn tìm một nơi thật an toàn và thoải mái 🛡️",
            'surprise': "Ôi thú vị quá! 🤩 Chuyến đi bất ngờ thường mang lại nhiều trải nghiệm đáng nhớ!",
            'disgust': "Mình hiểu cảm giác khó chịu đó 🍃 Một không gian trong lành sẽ giúp bạn refresh tinh thần!",
            'neutral': "Rất vui được hỗ trợ bạn! 😊"
        }
        
        # Context-based recommendations
        context_suggestions = {
            'heartbreak_recovery': "Mình gợi ý những nơi có không gian healing, view đẹp giúp tâm hồn nhẹ nhàng hơn 🌊",
            'business_trip': "Cho chuyến công tác, quan trọng là tiện nghi và vị trí thuận lợi 🏢",
            'solo_adventure': "Đi một mình thật tự do! Bạn sẽ có không gian riêng và những trải nghiệm mới 🎒",
            'workation': "Perfect cho workation! Mình sẽ tìm nơi có wifi tốt và không gian làm việc thoải mái 💻"
        }
        
        # Build intelligent response
        response_parts = []
        
        # Emotional empathy
        if emotion in emotional_responses:
            response_parts.append(emotional_responses[emotion])
        
        # Context understanding
        if primary_context in context_suggestions:
            response_parts.append(context_suggestions[primary_context])
        
        # Personality-based suggestion
        personality_type = insights['personality']['personality_type']
        response_parts.append(f"Với phong cách {personality_type}, mình nghĩ bạn sẽ thích:")
        
        # Add specific recommendations based on AI analysis
        response_parts.extend(self._get_personalized_suggestions(insights))
        
        return "\n\n".join(response_parts)
    
    def _get_personalized_suggestions(self, insights):
        """Đề xuất cá nhân hóa dựa trên phân tích AI"""
        suggestions = []
        
        # Dựa trên sentiment
        if insights['sentiment']['emotion'] in ['sadness', 'fear']:
            suggestions.append("• Nơi yên tĩnh, view thiên nhiên giúp thư giãn")
            suggestions.append("• Khách sạn có spa và dịch vụ wellness")
        
        # Dựa trên personality
        personality = insights['personality']['dominant_traits']
        if 'extroverted' in personality:
            suggestions.append("• Khu vực có hoạt động social và giao lưu")
        if 'introverted' in personality:
            suggestions.append("• Không gian riêng tư, ít đông đúc")
        if 'wellness_focused' in personality:
            suggestions.append("• Dịch vụ yoga, thiền và chăm sóc sức khỏe")
        
        return suggestions if suggestions else ["• Khách sạn có rating cao và dịch vụ tốt"]
    
    def _get_recommendation_strategy(self, insights):
        """Xác định chiến lược đề xuất"""
        context = insights['context']['primary_context']
        emotion = insights['sentiment']['emotion']
        
        strategies = {
            'heartbreak_recovery': 'healing_focus',
            'business_trip': 'practical_focus', 
            'workation': 'productivity_focus',
            'solo_adventure': 'experience_focus'
        }
        
        return strategies.get(context, 'balanced_focus')
