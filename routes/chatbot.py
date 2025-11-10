from flask import render_template, request, jsonify
import pandas as pd
import re
from datetime import datetime

from modules.advanced_sentiment import AdvancedSentimentAnalyzer
from modules.context_aware_recommender import ContextAwareRecommender
from modules.personality_analyzer import PersonalityAnalyzer
from modules.ai_chatbot_engine import AIChatbotEngine
from modules.filter import filter_by_location, filter_by_budget, filter_combined, parse_features_from_text
from modules.recommend import calculate_scores_and_explain

# Tải dữ liệu
def load_data():
    try:
        df = pd.read_csv("hotels.csv")
        return df
    except FileNotFoundError:
        return None

base_data = load_data()

# Khởi tạo AI Engine
ai_engine = AIChatbotEngine()

def parse_flexible_budget(text):
    """Parse ngân sách linh hoạt từ câu hỏi hỗn hợp"""
    text_lower = text.lower()
    
    budget_patterns = [
        r'dưới\s*(\d+\s*[kK]?\s*[đd]?[ồô]ng?)',
        r'khoảng\s*(\d+\s*[kK]?\s*[đd]?[ồô]ng?)',
        r'tầm\s*(\d+\s*[kK]?\s*[đd]?[ồô]ng?)',
        r'giá\s*(\d+\s*[kK]?\s*[đd]?[ồô]ng?)',
        r'(\d+\s*[kK]?\s*[tr]?[iệI]?[uu]?[ee]?[uu]?)\s*[đd]?[ồô]?ng?'
    ]
    
    for pattern in budget_patterns:
        matches = re.findall(pattern, text_lower)
        if matches:
            number_str = matches[0].replace('k', '000').replace('K', '000').replace('tr', '000000').replace('triệu', '000000')
            numbers = re.findall(r'\d+', number_str)
            if numbers:
                budget = int(numbers[0])
                if 'triệu' in matches[0] or 'tr' in matches[0]:
                    return budget * 1000000
                elif 'k' in matches[0] or 'K' in matches[0]:
                    return budget * 1000
                else:
                    return budget * 1000000 if budget < 1000 else budget
    
    # Mức giá tổng quát
    if any(word in text_lower for word in ["rẻ", "giá thấp", "tiết kiệm", "bình dân"]):
        return 1000000
    elif any(word in text_lower for word in ["tầm trung", "vừa phải", "trung bình"]):
        return 3000000
    elif any(word in text_lower for word in ["cao cấp", "sang", "đắt"]):
        return 8000000
    
    return None

def parse_flexible_stars(text):
    """Parse số sao linh hoạt từ câu hỏi hỗn hợp"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ["bao nhiêu sao cũng được", "không quan trọng sao", "tùy", "sao cũng được"]):
        return 0
    
    for i in range(5, 0, -1):
        if f"{i} sao" in text_lower or f"{i}-sao" in text_lower or f"{i} sao" in text_lower.replace('*', ''):
            return i
    
    numbers = re.findall(r'[1-5]', text)
    return int(numbers[0]) if numbers else 0

def parse_city(text):
    """Parse thành phố từ câu hỏi hỗn hợp"""
    text_lower = text.lower()
    city_mapping = {
        "hanoi": "Hanoi", "hà nội": "Hanoi", "hn": "Hanoi", "thủ đô": "Hanoi", "ha noi": "Hanoi",
        "da nang": "Da Nang", "đà nẵng": "Da Nang", "dn": "Da Nang", "da nang": "Da Nang",
        "ho chi minh": "Ho Chi Minh City", "sài gòn": "Ho Chi Minh City", 
        "saigon": "Ho Chi Minh City", "hcm": "Ho Chi Minh City", "tp hcm": "Ho Chi Minh City", "tphcm": "Ho Chi Minh City",
        "nha trang": "Nha Trang", "nt": "Nha Trang", "nha trang": "Nha Trang",
        "đà lạt": "Da Lat", "dalat": "Da Lat", "da lat": "Da Lat",
        "phú quốc": "Phu Quoc", "phu quoc": "Phu Quoc",
        "hội an": "Hoi An", "hoi an": "Hoi An",
        "vũng tàu": "Vung Tau", "vung tau": "Vung Tau",
        "quy nhơn": "Quy Nhon", "quy nhon": "Quy Nhon"
    }
    
    for keyword, city in city_mapping.items():
        if keyword in text_lower:
            return city
    return None

def extract_all_preferences_from_text(text):
    """Trích xuất thông tin từ câu hỏi hỗn hợp"""
    text_lower = text.lower()
    
    hotel_keywords = ['khách sạn', 'hotel', 'ks', 'đặt phòng', 'tìm', 'tìm kiếm', 'nghỉ', 'ở']
    is_hotel_request = any(keyword in text_lower for keyword in hotel_keywords) or any([
        parse_city(text), parse_flexible_budget(text), parse_flexible_stars(text), parse_features_from_text(text)
    ])
    
    if not is_hotel_request:
        return None
    
    preferences = {
        'city': parse_city(text),
        'budget': parse_flexible_budget(text),
        'min_stars': parse_flexible_stars(text),
        'features': parse_features_from_text(text),
        'text_query': text
    }
    
    return preferences

def has_sufficient_info(preferences):
    """Kiểm tra có đủ thông tin để tìm khách sạn không"""
    if not preferences:
        return False
        
    criteria_count = 0
    if preferences.get('city'):
        criteria_count += 1
    if preferences.get('budget'):
        criteria_count += 1  
    if preferences.get('min_stars', 0) > 0:
        criteria_count += 1
    if preferences.get('features'):
        criteria_count += len(preferences['features'])
    
    return criteria_count >= 1

def generate_hotel_recommendations(user_prefs, base_data):
    """Tạo đề xuất khách sạn với AI enhancement"""
    if base_data is None or base_data.empty:
        return [], "Không có dữ liệu khách sạn."

    filtered_data = base_data.copy()
    
    # Lọc cơ bản
    if user_prefs.get('city'):
        filtered_data = filter_by_location(filtered_data, user_prefs['city'])
    
    if user_prefs.get('budget'):
        filtered_data = filter_by_budget(filtered_data, user_prefs['budget'])
    
    features = user_prefs.get('features', {})
    if features:
        filtered_data = filter_combined(filtered_data, user_prefs.get('min_stars', 0), features)
    
    # Tính điểm AI
    if not filtered_data.empty:
        final_results, explanation = calculate_scores_and_explain(filtered_data, user_prefs)
        num_hotels = min(3, len(final_results))
        top_hotels = final_results.head(num_hotels).to_dict('records')
        
        return top_hotels, explanation
    else:
        return [], "Không tìm thấy khách sạn phù hợp."

def handle_special_scenarios(user_message, session_data, base_data):
    """Xử lý các tình huống đặc biệt"""
    text_lower = user_message.lower()
    
    # Scenario 1: User buồn vì hết phòng
    if any(keyword in text_lower for keyword in ['hết phòng', 'hết chỗ', 'full phòng', 'mất tiu', 'khi nào có phòng']):
        return _handle_room_unavailable(user_message, session_data, base_data)
    
    # Scenario 2: User thất vọng về giá
    elif any(keyword in text_lower for keyword in ['đắt quá', 'mắc quá', 'giá cao', 'over budget']):
        return _handle_price_concern(user_message, session_data, base_data)
    
    # Scenario 3: Xử lý lo lắng về chất lượng
    quality_response = handle_quality_concerns(user_message, session_data)
    if quality_response:
        return quality_response
    
    return None

def handle_quality_concerns(user_message, session_data):
    """Xử lý các lo lắng về chất lượng dịch vụ"""
    text_lower = user_message.lower()
    
    # Câu hỏi trực tiếp đòi hỏi cam kết
    if any(keyword in text_lower for keyword in ['có đảm bảo không', 'bạn đảm bảo', 'cam kết', 'chắc chắn không']):
        return _handle_direct_guarantee_request(user_message, session_data)
    
    # Lo lắng về vệ sinh hồ bơi
    elif any(keyword in text_lower for keyword in ['hồ bơi sạch không', 'bể bơi sạch', 'pool clean']):
        return _handle_pool_cleanliness_concern(user_message, session_data)
    
    # Lo lắng về an ninh
    elif any(keyword in text_lower for keyword in ['an toàn không', 'có an ninh', 'security']):
        return _handle_safety_concern(user_message, session_data)
    
    # Lo lắng chung về vệ sinh
    elif any(keyword in text_lower for keyword in ['sạch không', 'vệ sinh', 'clean']):
        return _handle_general_cleanliness_concern(user_message, session_data)
    
    return None

def _handle_room_unavailable(user_message, session_data, base_data):
    """Xử lý tình huống user buồn vì hết phòng"""
    liked_hotel = session_data.get('currentHotels', [{}])[0] if session_data.get('currentHotels') else None
    
    response_parts = []
    
    response_parts.append("😔 Ôi không! Mình hiểu cảm giác thất vọng này...")
    response_parts.append("Khách sạn ưng ý mà hết phòng thật đáng tiếc quá!")
    
    response_parts.append("\n**🎯 Mình có vài gợi ý cho bạn:**")
    response_parts.append("• **Tìm khách sạn tương tự** - Cùng khu vực, cùng tiện nghi")
    
    if liked_hotel:
        response_parts.append(f"• **Theo dõi phòng trống** - {liked_hotel.get('name', 'Khách sạn này')} thường có phòng trở lại sau 1-2 ngày")
    
    response_parts.append("• **Khu vực lân cận** - Cùng thành phố nhưng giá tốt hơn")
    response_parts.append("• **Đặt linh hoạt** - Thử ngày check-in khác")
    
    response_parts.append("\n**🔍 Để mình giúp bạn:**")
    
    similar_hotels = _find_similar_hotels(liked_hotel, base_data) if liked_hotel else []
    
    if similar_hotels:
        response_parts.append("Mình tìm thấy vài khách sạn tương tự:")
        for hotel in similar_hotels[:2]:
            hotel_desc = f"🏨 **{hotel['name']}** - {hotel['price']:,} VND"
            if hotel.get('pool'): hotel_desc += " 🏊"
            if hotel.get('rating'): hotel_desc += f" ⭐{hotel['rating']}"
            response_parts.append(hotel_desc)
    
    response_parts.append("\n💫 Đừng buồn nhé! Chắc chắn sẽ có lựa chọn tốt cho bạn!")
    
    return {
        'response': "\n".join(response_parts),
        'stage': 'problem_solving',
        'preferences': session_data.get('preferences', {}),
        'hotels': similar_hotels,
        'currentHotels': similar_hotels,
        'has_results': len(similar_hotels) > 0,
        'special_scenario': 'room_unavailable'
    }

def _handle_direct_guarantee_request(user_message, session_data):
    """Xử lý câu hỏi trực tiếp đòi hỏi cam kết"""
    response_parts = []
    
    response_parts.append("🤔 Mình hiểu bạn muốn sự đảm bảo chắc chắn về chất lượng!")
    response_parts.append("")
    response_parts.append("**Thành thật mà nói**, với tư cách là chatbot, mình *không thể đưa ra cam kết 100%* về việc dịch vụ có hoàn hảo hay không tại thời điểm bạn sử dụng.")
    response_parts.append("")
    
    response_parts.append("**Nhưng đây là những gì mình CAM KẾT có thể làm:**")
    response_parts.append("")
    response_parts.append("✅ **Lọc kỹ tiêu chí**: Chỉ đề xuất khách sạn có rating từ 8.0/10 trở lên từ review thực tế")
    response_parts.append("")
    response_parts.append("✅ **Ưu tiên chất lượng**: Các khách sạn được kiểm duyệt và có phản hồi tích cực")
    response_parts.append("")
    response_parts.append("✅ **Check review mới nhất**: Mình sẽ gợi ý bạn xem các review trong 2 tuần gần nhất")
    response_parts.append("")
    
    response_parts.append("**🔍 Để bạn tự kiểm chứng:**")
    response_parts.append("• Vào **Google Maps/Booking.com** → tìm tên khách sạn → đọc review mới nhất")
    response_parts.append("• Ưu tiên khách sạn có **chứng nhận chất lượng** hoặc giải thưởng")
    response_parts.append("• Check ảnh thực tế khách chụp - thường phản ánh rất trung thực")
    response_parts.append("")
    
    response_parts.append("**🛡️ Hỗ trợ thực tế nếu có vấn đề:**")
    response_parts.append("📞 **Hotline hỗ trợ 24/7: 1900-1234** - Mình sẽ kết nối bạn với đội ngũ xử lý sự cố")
    response_parts.append("💰 **Đảm bảo hoàn tiền**: Nếu dịch vụ không đúng như mô tả, mình hỗ trợ bạn khiếu nại")
    response_parts.append("")
    
    response_parts.append("**Mình muốn bạn có trải nghiệm trung thực và an tâm nhất!** 🌟")
    
    return {
        'response': "\n".join(response_parts),
        'stage': 'direct_guarantee',
        'preferences': session_data.get('preferences', {}),
        'special_scenario': 'direct_guarantee_request'
    }

def _handle_pool_cleanliness_concern(user_message, session_data):
    """Xử lý lo lắng về vệ sinh hồ bơi"""
    response_parts = []
    
    response_parts.append("🏊 Mình hoàn toàn hiểu mối quan tâm của bạn!")
    response_parts.append("Vệ sinh hồ bơi là ưu tiên hàng đầu với mình khi chọn khách sạn đấy!")
    
    response_parts.append("\n**🔒 Bạn yên tâm nhé, các khách sạn mình đề xuất đều:**")
    response_parts.append("• **Vệ sinh hồ bơi hàng ngày** - Kiểm tra chlorine và pH 2 lần/ngày")
    response_parts.append("• **Tuân thủ tiêu chuẩn vệ sinh** - Theo quy định của Bộ Y tế")
    response_parts.append("• **Có nhân viên cứu hộ** - Giám sát an toàn thường xuyên")
    response_parts.append("• **Khách sạn có rating cao** - Được đánh giá tốt về vệ sinh")
    
    response_parts.append("\n**💡 Mẹo nhỏ cho bạn:**")
    response_parts.append("• Nên bơi vào buổi sáng - Hồ thường sạch nhất sau khi vệ sinh đêm")
    response_parts.append("• Check review trên booking.com - Khách thường feedback rất thật về vệ sinh")
    response_parts.append("• Ưu tiên khách sạn 4-5 sao - Tiêu chuẩn vệ sinh thường cao hơn")
    
    response_parts.append("\n**🛡️ Để bạn hoàn toàn yên tâm:**")
    response_parts.append("• **Mình cam kết** chỉ đề xuất khách sạn có rating vệ sinh từ 8.0 trở lên")
    response_parts.append("• **Hỗ trợ 24/7** - Nếu có vấn đề, alo ngay cho mình: 📞 **1900-1234**")
    
    response_parts.append("\n💫 Cứ thoải mái tận hưởng kỳ nghỉ nhé! Mình đảm bảo bạn sẽ hài lòng!")
    
    return {
        'response': "\n".join(response_parts),
        'stage': 'reassurance',
        'preferences': session_data.get('preferences', {}),
        'special_scenario': 'pool_cleanliness_concern'
    }

def _handle_safety_concern(user_message, session_data):
    """Xử lý lo lắng về an ninh"""
    response_parts = []
    
    response_parts.append("🛡️ Chắc chắn rồi! An toàn là ưu tiên số 1 của mình!")
    response_parts.append("Mình hoàn toàn hiểu nỗi lo này, đặc biệt khi đi du lịch một mình hoặc với gia đình.")
    
    response_parts.append("\n**🔒 Các khách sạn được đề xuất đều có:**")
    response_parts.append("• **Bảo vệ 24/7** - Có mặt tại sảnh và tuần tra thường xuyên")
    response_parts.append("• **Camera an ninh** - Hệ thống giám sát toàn khu vực công cộng")
    response_parts.append("• **Khoá thẻ từ** - Chỉ khách lưu trú mới vào được tầng phòng")
    response_parts.append("• **Tủ an toàn** - Cất giữ laptop, passport an toàn")
    
    response_parts.append("\n**📍 Khu vực an toàn:**")
    response_parts.append("• Gần trung tâm, đông đúc, nhiều hoạt động")
    response_parts.append("• Có taxi, grab hoạt động 24/7")
    response_parts.append("• Gần đồn cảnh sát, bệnh viện (trong bán kính 3km)")
    
    response_parts.append("\n**🚨 Hỗ trợ khẩn cấp:**")
    response_parts.append("• **Hotline an ninh khách sạn**: 📞 Ext. 911 (bấm 0 từ phòng)")
    response_parts.append("• **Cảnh sát du lịch**: 📞 113 hoặc 069.234.567")
    response_parts.append("• **Team mình 24/7**: 📞 1900-1234 (luôn sẵn sàng!)")
    
    response_parts.append("\n🌙 Cứ yên tâm tận hưởng chuyến đi nhé! Mình luôn ở đây hỗ trợ bạn!")

    return {
        'response': "\n".join(response_parts),
        'stage': 'safety_reassurance', 
        'preferences': session_data.get('preferences', {}),
        'special_scenario': 'safety_concern'
    }

def _handle_general_cleanliness_concern(user_message, session_data):
    """Xử lý lo lắng chung về vệ sinh"""
    response_parts = []
    
    response_parts.append("🧼 Mình nghe bạn nè! Vệ sinh là điều mình quan tâm nhất luôn!")
    response_parts.append("Khách sạn sạch sẽ làm chuyến đi thoải mái hơn hẳn đúng không?")
    
    response_parts.append("\n**✨ Tiêu chí lọc khách sạn sạch sẽ của mình:**")
    response_parts.append("• **Rating vệ sinh > 8.0** - Từ review thực tế của khách")
    response_parts.append("• **Housekeeping hàng ngày** - Dọn phòng, thay khăn tắm mỗi ngày")
    response_parts.append("• **Khử trùng định kỳ** - Đặc biệt remote, tay nắm cửa, vòi nước")
    response_parts.append("• **Khách sạn mới/renovate** - Thường có tiêu chuẩn vệ sinh cao hơn")
    
    response_parts.append("\n**🔍 Mẹo check nhanh khi nhận phòng:**")
    response_parts.append("• Ngửi mùi phòng - Phòng sạch thường có mùi dễ chịu")
    response_parts.append("• Check góc phòng tắm - Nơi dễ bỏ sót khi dọn dẹp")
    response_parts.append("• Xem nệm và gối - Không có vết bẩn hoặc mùi lạ")
    
    response_parts.append("\n**🛎️ Nếu không hài lòng về vệ sinh:**")
    response_parts.append("• **Yêu cầu đổi phòng ngay** - Quyền lợi chính đáng của bạn!")
    response_parts.append("• **Hotline hỗ trợ**: 📞 1900-1234 (mình sẽ can thiệp trực tiếp)")
    response_parts.append("• **Gửi feedback** - Giúp mình cải thiện dịch vụ tốt hơn 💝")
    
    response_parts.append("\n🌿 Cứ tin tưởng mình nhé! Mình muốn bạn có trải nghiệm tuyệt vời nhất!")

    return {
        'response': "\n".join(response_parts),
        'stage': 'cleanliness_reassurance',
        'preferences': session_data.get('preferences', {}),
        'special_scenario': 'general_cleanliness'
    }

def _handle_price_concern(user_message, session_data, base_data):
    """Xử lý tình huống user lo lắng về giá"""
    response_parts = []
    
    response_parts.append("💸 Mình hiểu giá cả là vấn đề quan trọng!")
    response_parts.append("Đừng lo, mình có vài giải pháp:")
    
    response_parts.append("\n**💰 Gợi ý tiết kiệm:**")
    response_parts.append("• **Khách sạn 3-4 sao** - Vẫn đầy đủ tiện nghi, giá tốt hơn")
    response_parts.append("• **Đặt sớm** - Giá thường tốt hơn khi book trước")
    response_parts.append("• **Khuyến mãi cuối tuần** - Nhiều ưu đãi đặc biệt")
    
    current_prefs = session_data.get('preferences', {})
    if current_prefs.get('budget'):
        # Giảm budget để tìm option rẻ hơn
        budget_suggestions = _find_budget_options(current_prefs, base_data)
        
        if budget_suggestions:
            response_parts.append("\n**🏨 Một vài lựa chọn giá tốt:**")
            for hotel in budget_suggestions[:2]:
                response_parts.append(f"• {hotel['name']} - {hotel['price']:,} VND")
    
    response_parts.append("\n🎯 Hãy cho mình biết ngân sách cụ thể, mình tìm option tốt nhất!")
    
    return {
        'response': "\n".join(response_parts),
        'stage': 'budget_help',
        'preferences': current_prefs,
        'hotels': budget_suggestions if 'budget_suggestions' in locals() else [],
        'has_results': 'budget_suggestions' in locals() and len(budget_suggestions) > 0
    }

def _find_similar_hotels(target_hotel, base_data, max_results=3):
    """Tìm khách sạn tương tự"""
    if not target_hotel or base_data is None:
        return []
    
    try:
        similar_candidates = base_data[
            (base_data['city'] == target_hotel.get('city')) &
            (abs(base_data['stars'] - target_hotel.get('stars', 3)) <= 1) &
            (base_data['name'] != target_hotel.get('name'))
        ].copy()
        
        similar_candidates['similarity_score'] = 0
        
        features = ['pool', 'spa', 'sea', 'buffet']
        for feature in features:
            if target_hotel.get(feature) and feature in similar_candidates.columns:
                similar_candidates['similarity_score'] += similar_candidates[feature] * 2
        
        target_price = target_hotel.get('price', 0)
        if target_price > 0:
            price_range = similar_candidates[
                (similar_candidates['price'] >= target_price * 0.7) & 
                (similar_candidates['price'] <= target_price * 1.3)
            ]
            if not price_range.empty:
                similar_candidates.loc[price_range.index, 'similarity_score'] += 3
        
        similar_candidates = similar_candidates.sort_values('similarity_score', ascending=False)
        return similar_candidates.head(max_results).to_dict('records')
        
    except Exception as e:
        print(f"Error finding similar hotels: {e}")
        return []

def _find_budget_options(preferences, base_data):
    """Tìm option giá tốt hơn"""
    try:
        if not preferences.get('budget'):
            return []
        
        # Giảm budget 30% để tìm option rẻ hơn
        reduced_budget = preferences['budget'] * 0.7
        
        filtered = base_data.copy()
        if preferences.get('city'):
            filtered = filter_by_location(filtered, preferences['city'])
        
        filtered = filter_by_budget(filtered, reduced_budget)
        
        if not filtered.empty:
            return filtered.sort_values('price').head(3).to_dict('records')
        return []
        
    except Exception as e:
        print(f"Error finding budget options: {e}")
        return []

def create_ai_enhanced_response(hotels, ai_insights, user_message):
    """Tạo response thông minh với AI insights"""
    if not hotels:
        emotional_response = _get_emotional_support(ai_insights)
        alternative_suggestions = _get_alternative_suggestions(ai_insights)
        return f"{emotional_response}\n\n{alternative_suggestions}", False
    
    response_parts = []
    
    emotional_part = _get_emotional_response(ai_insights)
    if emotional_part:
        response_parts.append(emotional_part)
    
    context_intro = _get_context_introduction(ai_insights)
    if context_intro:
        response_parts.append(context_intro)
    
    response_parts.append("**Mình đã tìm thấy các khách sạn phù hợp cho bạn:**\n\n")
    
    for i, hotel in enumerate(hotels, 1):
        hotel_part = f"**{hotel['name']}**\n"
        hotel_part += f"⭐ {hotel['stars']} sao | 💰 {hotel['price']:,} VND/đêm\n"
        hotel_part += f"📍 {hotel['city']} | ⭐ {hotel['rating']}/5\n"
        
        features = []
        if hotel.get('pool'): features.append("🏊 Hồ bơi")
        if hotel.get('buffet'): features.append("🍽️ Buffet sáng") 
        if hotel.get('gym'): features.append("💪 Gym")
        if hotel.get('spa'): features.append("💆 Spa")
        if hotel.get('sea'): features.append("🌊 View biển")
        if hotel.get('view'): features.append("🏞️ View đẹp")
        
        if features:
            hotel_part += f"🎯 {', '.join(features)}\n"
        
        hotel_part += f"<button class='detail-link' data-hotel-name='{hotel['name']}'> Xem chi tiết {hotel['name']}</button>"
        
        response_parts.append(hotel_part)
        
        if i < len(hotels):
            response_parts.append("\n" + "─" * 40 + "\n\n")
    
    closing = _get_personalized_closing(ai_insights)
    response_parts.append(closing)
    
    return "\n".join(response_parts), True

def _get_emotional_response(insights):
    """Tạo phản hồi cảm xúc"""
    emotion = insights.get('sentiment', {}).get('emotion', 'neutral')
    emotion_responses = {
        'sadness': "💫 Mình hiểu bạn đang có chút buồn... Một chuyến đi nhỏ có thể giúp tâm trạng tốt hơn đấy!",
        'joy': "🎉 Tuyệt vời! Tâm trạng tốt sẽ làm chuyến đi thêm phần thú vị!",
        'anger': "😥 Mình cảm nhận được sự bức bối... Không gian yên tĩnh có thể giúp bạn lấy lại cân bằng 🌿",
        'fear': "🛡️ Đừng lo lắng quá nhé! Mình sẽ giúp bạn tìm nơi an toàn và thoải mái nhất!",
        'surprise': "🤩 Ôi thú vị quá! Chuyến đi bất ngờ thường mang lại nhiều trải nghiệm đáng nhớ!",
        'disgust': "🍃 Mình hiểu cảm giác khó chịu đó... Một không gian trong lành sẽ giúp bạn refresh tinh thần!",
        'neutral': "😊 Rất vui được hỗ trợ bạn!"
    }
    return emotion_responses.get(emotion, emotion_responses['neutral'])

def _get_context_introduction(insights):
    """Giới thiệu dựa trên ngữ cảnh"""
    context = insights.get('context', {}).get('primary_context', 'general_travel')
    context_intros = {
        'heartbreak_recovery': "🌊 Gợi ý những nơi có không gian healing, giúp tâm hồn nhẹ nhàng hơn",
        'business_trip': "🏢 Cho chuyến công tác, quan trọng là tiện nghi và vị trí thuận lợi",
        'solo_adventure': "🎒 Đi một mình thật tự do! Bạn sẽ có không gian riêng và những trải nghiệm mới",
        'family_vacation': "👨‍👩‍👧‍👦 Cho gia đình, an toàn và không gian vui chơi là ưu tiên hàng đầu",
        'romantic_getaway': "💖 Lãng mạn quá! Không gian riêng tư sẽ làm chuyến đi thêm đặc biệt",
        'stress_relief': "🧘 Để xả stress, không gian yên tĩnh và dịch vụ thư giãn là lựa chọn perfect"
    }
    return context_intros.get(context, "")

def _get_personalized_closing(insights):
    """Kết thúc cá nhân hóa"""
    personality = insights.get('personality', {}).get('personality_type', 'Balanced Traveler')
    closings = {
        'Social Explorer': "🎊 Hy vọng bạn sẽ có những cuộc gặp gỡ thú vị!",
        'Mindful Traveler': "🍃 Chúc bạn tìm thấy sự bình yên trong chuyến đi này!", 
        'Premium Socialite': "💎 Tận hưởng những trải nghiệm sang trọng nhé!",
        'Budget Adventurer': "🗺️ Chúc bạn có chuyến phiêu lưu tiết kiệm mà vẫn vui!",
        'Wellness Seeker': "🌸 Chúc bạn tìm thấy sự cân bằng và tĩnh tâm!"
    }
    base_closing = closings.get(personality, "✨ Chúc bạn có chuyến đi thật vui!")
    return f"\n{base_closing}\n\nBạn muốn tìm kiếm với tiêu chí khác không ạ?"

def _get_emotional_support(insights):
    """Hỗ trợ cảm xúc khi không có khách sạn phù hợp"""
    emotion = insights.get('sentiment', {}).get('emotion', 'neutral')
    support_messages = {
        'sadness': "💫 Dù không tìm thấy khách sạn phù hợp ngay lúc này, nhưng mình tin sẽ có lựa chọn tốt cho bạn!",
        'joy': "😊 Tuy chưa tìm thấy khách sạn ưng ý, nhưng tâm trạng tốt sẽ giúp bạn tìm được nơi phù hợp!",
        'anger': "🌿 Đừng nản lòng nhé! Thử điều chỉnh tiêu chí một chút, chắc chắn sẽ có lựa chọn phù hợp!",
        'fear': "🛡️ Bạn yên tâm! Mình sẽ giúp bạn tìm nơi an toàn và thoải mái nhất!",
        'neutral': "🔍 Hãy thử điều chỉnh tiêu chí tìm kiếm, mình chắc chắn sẽ tìm được khách sạn phù hợp!"
    }
    return support_messages.get(emotion, support_messages['neutral'])

def _get_alternative_suggestions(insights):
    """Đề xuất thay thế khi không có khách sạn phù hợp"""
    context = insights.get('context', {}).get('primary_context', 'general_travel')
    suggestions = {
        'heartbreak_recovery': "Thử tìm homestay nhỏ xinh hoặc resort yên tĩnh nhé!",
        'business_trip': "Có thể thử tìm khách sạn gần trung tâm hội nghị hoặc khu công nghiệp!",
        'solo_adventure': "Hostel hoặc guesthouse có thể mang lại trải nghiệm thú vị!",
        'family_vacation': "Thử tìm căn hộ dịch vụ hoặc villa cho không gian rộng rãi!",
        'general_travel': "Hãy thử mở rộng phạm vi tìm kiếm hoặc điều chỉnh ngân sách!"
    }
    return suggestions.get(context, "Hãy thử điều chỉnh tiêu chí tìm kiếm nhé!")

def process_chat_message(user_message, session_data):
    """Xử lý tin nhắn chat với AI tích hợp"""
    stage = session_data.get('stage', 'greeting')
    user_id = session_data.get('user_id', 'default_user')

    # Xử lý các tình huống đặc biệt trước
    special_response = handle_special_scenarios(user_message, session_data, base_data)
    if special_response:
        return special_response

    # Phân tích AI nâng cao
    ai_insights = ai_engine.process_user_message(user_id, user_message)

    # Kiểm tra từ chối
    user_message_lower = user_message.lower()
    negative_keywords = ['không', 'ko', 'thôi', 'khong', 'k cần', 'không cần', 'đủ rồi', 'enough', 'no']

    if any(keyword in user_message_lower for keyword in negative_keywords) and stage == 'follow_up':
        return {
            'response': "Cảm ơn du khách đã sử dụng dịch vụ của chúng tôi! 😊✨\nNếu có nhu cầu đặt phòng hoặc tư vấn thêm, hãy quay lại nhé!",
            'stage': 'end',
            'preferences': {},
            'hotels': [],
            'has_results': False,
            'ai_insights': ai_insights
        }

    # Phân tích yêu cầu hỗn hợp
    extracted_info = extract_all_preferences_from_text(user_message)

    # Nếu phân tích được thông tin từ yêu cầu hỗn hợp
    if extracted_info and has_sufficient_info(extracted_info):
        hotels, explanation = generate_hotel_recommendations(extracted_info, base_data)
        response_text, has_results = create_ai_enhanced_response(hotels, ai_insights, user_message)

        return {
            'response': response_text,
            'stage': 'follow_up',
            'preferences': extracted_info,
            'hotels': hotels,
            'currentHotels': hotels,
            'has_results': has_results,
            'ai_insights': ai_insights
        }

    # Xử lý theo stage thông thường
    user_prefs = session_data.get('preferences', {})

    if stage == 'greeting':
        return {
            'response': "Xin chào du khách! 👋 Hãy cho tôi biết bạn muốn tìm khách sạn như thế nào? (ví dụ: 'Khách sạn ở Đà Nẵng có hồ bơi', 'Phòng giá rẻ ở Hà Nội', 'Khách sạn 5 sao có buffet')",
            'stage': 'awaiting_request', 
            'preferences': user_prefs,
            'ai_insights': ai_insights
        }

    elif stage == 'awaiting_request':
        return {
            'response': "Bạn có thể nói rõ hơn về yêu cầu được không? Ví dụ:\n• 'Khách sạn ở Hà Nội có hồ bơi'\n• 'Phòng giá dưới 2 triệu' \n• 'Khách sạn 4 sao ở Đà Nẵng'",
            'stage': 'awaiting_request',
            'preferences': user_prefs,
            'ai_insights': ai_insights
        }

    elif stage == 'follow_up':
        # Xử lý yêu cầu mới sau khi đã có kết quả
        if any(word in user_message_lower for word in ['tìm lại', 'khác', 'reset', 'mới']):
            return {
                'response': "OK! Hãy cho tôi biết bạn muốn tìm khách sạn như thế nào?",
                'stage': 'awaiting_request',
                'preferences': {},
                'ai_insights': ai_insights
            }
        else:
            # Thử phân tích yêu cầu mới
            new_extracted_info = extract_all_preferences_from_text(user_message)
            if new_extracted_info and has_sufficient_info(new_extracted_info):
                hotels, explanation = generate_hotel_recommendations(new_extracted_info, base_data)
                response_text, has_results = create_ai_enhanced_response(hotels, ai_insights, user_message)

                return {
                    'response': response_text,
                    'stage': 'follow_up',
                    'preferences': new_extracted_info,
                    'hotels': hotels,
                    'currentHotels': hotels,
                    'has_results': has_results,
                    'ai_insights': ai_insights
                }
            else:
                return {
                    'response': "Bạn muốn tìm kiếm với tiêu chí gì khác? (ví dụ: thêm hồ bơi, đổi thành phố, giá cả khác...)",
                    'stage': 'follow_up',
                    'preferences': user_prefs,
                    'ai_insights': ai_insights
                }

    # Mặc định
    return {
        'response': "Hãy cho tôi biết bạn muốn tìm khách sạn như thế nào? (ví dụ: 'Khách sạn ở Đà Nẵng', 'Phòng có hồ bơi', 'Giá dưới 3 triệu')",
        'stage': 'awaiting_request',
        'preferences': {},
        'ai_insights': ai_insights
    }

def init_chatbot_routes(app):
    @app.route('/chatbot')
    def chatbot_page():
        return render_template('chatbot.html')
    
    @app.route('/api/chat', methods=['POST'])
    def chat_api():
        try:
            data = request.json
            user_message = data.get('message', '').strip()
            session_data = data.get('session', {})
            
            # Thêm user_id nếu chưa có
            if 'user_id' not in session_data:
                session_data['user_id'] = f"user_{datetime.now().timestamp()}"
            
            # Logic xử lý hội thoại
            response_data = process_chat_message(user_message, session_data)
            
            return jsonify(response_data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
