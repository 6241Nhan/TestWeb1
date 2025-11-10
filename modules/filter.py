import pandas as pd

def filter_by_location(df, location_city):
    """
    Lọc DataFrame dựa trên thành phố 
    """
    if not location_city: 
        return df

    location_lower = str(location_city).lower().strip()
    df_city_normalized = df['city'].str.lower().str.strip()
    
    filtered_df = df[df_city_normalized == location_lower]
    return filtered_df

def filter_by_budget(df, max_price):
    """
    Lọc DataFrame dựa trên ngân sách tối đa 
    Chỉ giữ lại các khách sạn có giá <= max_price.
    """
    if max_price <= 0: 
        return df

    df_price = pd.to_numeric(df['price'], errors='coerce')
    filtered_df = df[df_price <= max_price]
    return filtered_df

def filter_combined(df, min_stars, preferences):
    """
    Hàm lọc phức tạp, kết hợp nhiều tiêu chí.
    - Lọc theo số sao tối thiểu 
    - Lọc theo các sở thích : 'pool', 'buffet'
    """
    print(f"[Filter] Đang lọc với {min_stars} sao và sở thích {preferences}...")
    
   
    filtered_df = df.copy()
    
   
    if min_stars > 0:
        filtered_df = filtered_df[filtered_df['stars'] >= min_stars]

    for key, value in preferences.items():
        if value: 
            if key in filtered_df.columns:
                filtered_df = filtered_df[filtered_df[key] == True]
            else:
                print(f"Cảnh báo: Không tìm thấy cột '{key}' để lọc.")
                
    return filtered_df

def parse_features_from_text(text):
    """Trích xuất các tính năng từ câu hỏi tự nhiên - MỞ RỘNG"""
    text_lower = text.lower()
    features = {}
    
    # Các tính năng khách sạn - MỞ RỘNG THÊM
    feature_keywords = {
        'pool': ['hồ bơi', 'bể bơi', 'pool', 'bơi lội', 'swimming'],
        'buffet': ['buffet', 'buffet sáng', 'ăn sáng', 'bữa sáng', 'breakfast'],
        'gym': ['gym', 'phòng gym', 'thể hình', 'tập thể dục', 'fitness'],
        'spa': ['spa', 'massage', 'xông hơi', 'thư giãn'],
        'sea': ['biển', 'gần biển', 'view biển', 'bãi biển', 'biển đẹp', 'sea', 'beach'],
        'view': ['view', 'cảnh đẹp', 'tầm nhìn', 'view thành phố', 'city view'],
        'wifi': ['wifi', 'internet', 'mạng'],
        'parking': ['bãi đỗ', 'đỗ xe', 'parking', 'garage'],
        'breakfast': ['bữa sáng', 'ăn sáng', 'breakfast included'],
        'restaurant': ['nhà hàng', 'restaurant', 'quán ăn']
    }
    
    for feature, keywords in feature_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            features[feature] = True
    
    return features
