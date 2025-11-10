import pandas as pd

def calculate_scores_and_explain(df, all_prefs):
    """
    Hàm tính điểm, sắp xếp và giải thích 
    Trả về 2 giá trị: (dataframe_sorted, explanation_string)
    """
    print(f"[AI] Bắt đầu tính điểm. Sở thích: {all_prefs}")
    
    # Một danh sách để lưu lại các lý do giải thích
    explanation_log = ["Bắt đầu quá trình xếp hạng:"]
    
    # Tạo bản sao để tính toán
    df_scored = df.copy()
    
    # LỌC CỨNG (Hard Filter) ---
    min_stars = all_prefs.get('min_stars', 0)
    if min_stars > 0:
        df_scored = df_scored[df_scored['stars'] >= min_stars].copy()
        explanation_log.append(f"Loại bỏ các khách sạn dưới {min_stars} sao.")
    
    if df_scored.empty:
        return df_scored, "Không tìm thấy khách sạn nào sau khi lọc theo số sao."

    # TÍNH ĐIỂM (Scoring Logic) ---
    # 
    df_scored['recommend_score'] = df_scored['rating'] * 3

    # 1. Tính điểm sở thích 
    feature_scores = {
        'pool': 8,
        'buffet': 5, 
        'gym': 4,
        'spa': 4,
        'sea': 6,
        'view': 3
    }

    for feature, score in feature_scores.items():
        if all_prefs.get(feature, False):
            df_scored['recommend_score'] += df_scored[feature].apply(
                lambda has_feature: score if has_feature else -2
            )
            explanation_log.append(f"Ưu tiên khách sạn có {feature}.")

    # 2. Tính điểm Text 
    user_text = all_prefs.get('text', '').lower()
    user_query = all_prefs.get('text_query', '').lower()  # THÊM DÒNG NÀY
    combined_text = user_text + " " + user_query

    text_score = 0

    # Xử lý "bao nhiêu sao cũng được"
    if 'bao nhiêu sao cũng được' in combined_text or 'sao nào cũng được' in combined_text:
        explanation_log.append("Không yêu cầu số sao cụ thể.")
    
    # Xử lý "giá rẻ"
    if 'giá rẻ' in combined_text or 'rẻ' in combined_text or 'giá thấp' in combined_text:
        df_scored['recommend_score'] += (1 / df_scored['price']) * 1000000
        explanation_log.append("Ưu tiên khách sạn giá rẻ.")
    
    # Xử lý "nhiều đánh giá tích cực"
    if 'nhiều đánh giá tích cực' in combined_text or 'đánh giá tốt' in combined_text:
        df_scored['recommend_score'] += df_scored['rating'] * 2
        explanation_log.append("Ưu tiên khách sạn có đánh giá cao.")
    
    # Xử lý các từ khóa trong đánh giá
    review_keywords = {
        'biển đẹp': ['biển đẹp', 'view biển tuyệt', 'bãi biển đẹp'],
        'dịch vụ tốt': ['dịch vụ tốt', 'nhân viên thân thiện', 'phục vụ chu đáo'],
        'yên tĩnh': ['yên tĩnh', 'thanh bình', 'tĩnh lặng'],
        'view đẹp': ['view đẹp', 'cảnh đẹp', 'tầm nhìn đẹp']
    }
    
    for aspect, keywords in review_keywords.items():
        if any(keyword in combined_text for keyword in keywords):
            for keyword in keywords:
                mask = df_scored['review'].str.contains(keyword, case=False, na=False)
                text_score += mask * 6
            explanation_log.append(f"Tìm kiếm khách sạn có '{aspect}' trong đánh giá.")
    
    if 'biển' in user_text:
        text_score += df_scored['sea'].apply(lambda has_sea: 10 if has_sea else -3)
        explanation_log.append("Tìm kiếm từ khóa 'biển', ưu tiên khách sạn gần biển.")
    
    if 'yên tĩnh' in user_text:
        text_score += df_scored['review'].str.contains('yên tĩnh|thoải mái', case=False).apply(lambda x: 5 if x else 0)
        explanation_log.append("Tìm kiếm từ khóa 'yên tĩnh' trong đánh giá.")

    if 'dịch vụ' in user_text or 'thân thiện' in user_text:
         text_score += df_scored['review'].str.contains('dịch vụ|thân thiện', case=False).apply(lambda x: 4 if x else 0)
         explanation_log.append("Tìm kiếm từ khóa 'dịch vụ', 'thân thiện' trong đánh giá.")

    df_scored['recommend_score'] += text_score

    # SẮP XẾP (Sorting) ---
    # Sắp xếp theo yêu cầu mới
    final_results_sorted = df_scored.sort_values(by="recommend_score", ascending=False)
    explanation_log.append("Hoàn tất! Đã sắp xếp kết quả.")

    # TRẢ VỀ KẾT QUẢ ---
    final_explanation = " ".join(explanation_log)

    num_results = min(3, len(final_results_sorted))
    print(f"[AI] Trả về {num_results} khách sạn")
    
    return final_results_sorted, final_explanation

