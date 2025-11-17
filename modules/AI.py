import math
import pandas as pd
from datetime import datetime


def haversine(lat1, lon1, lat2, lon2):
    """Tính khoảng cách km giữa 2 tọa độ"""
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def month_to_season(month):
    if month in (3,4,5): return 'spring'
    if month in (6,7,8): return 'summer'
    if month in (9,10,11): return 'autumn'
    return 'winter'

# =========================
# 2️⃣ RULE CHO THỜI TIẾT & MÙA
# =========================
weather_rules = {
    'sunny': lambda hotel: 1.0 if ('pool_outdoor' in hotel['amenities'] or 'beach_nearby' in hotel['amenities']) else 0.3,
    'rain':  lambda hotel: 1.0 if ('indoor' in hotel['amenities'] or 'spa' in hotel['amenities'] or 'near_center' in hotel['amenities']) else 0.3,
    'cold':  lambda hotel: 1.0 if ('heating' in hotel['amenities'] or 'near_cafe' in hotel['amenities']) else 0.4,
    'hot':   lambda hotel: 1.0 if ('pool_outdoor' in hotel['amenities'] or 'aircon' in hotel['amenities']) else 0.4,
    'default': lambda hotel: 0.5
}

season_rules = {
    'spring': lambda hotel: 1.0 if 'garden_view' in hotel['amenities'] or 'romantic' in hotel['tags'] else 0.5,
    'summer': lambda hotel: 1.0 if ('beach_nearby' in hotel['amenities'] or 'pool_outdoor' in hotel['amenities']) else 0.4,
    'autumn': lambda hotel: 1.0 if 'city_view' in hotel['amenities'] or 'near_center' in hotel['amenities'] else 0.5,
    'winter': lambda hotel: 1.0 if ('heating' in hotel['amenities'] or 'spa' in hotel['amenities']) else 0.4
}
# =============================
# ĐỌC FILE CSV
# =============================
hotels_df = pd.read_csv("hotels.csv")
events_df = pd.read_csv("events.csv")


# =============================
# HÀM TÍNH ĐIỂM
# =============================
def score_event(hotel_row, events_df, ref_date):
    nearest_event = None
    min_days = None
    for _, ev in events_df.iterrows():
        if ev['city'] != selected_city:
            continue
        ev_date = datetime.fromisoformat(str(ev['date']))
        delta_days = (ev_date - ref_date).days
        if delta_days >= -1 and (min_days is None or delta_days < min_days):
            nearest_event = ev
            min_days = delta_days
    if nearest_event is not None:
        dist = haversine(hotel_row['lat'], hotel_row['lon'], nearest_event['lat'], nearest_event['lon'])
        return 1 / (dist + 1)
    return 0.1

def score_weather(hotel_row, condition):
    amenities = hotel_row['amenities'].split(';')
    rule = weather_rules.get(condition, weather_rules['default'])
    return rule(amenities)

def score_season(hotel_row, season_name):
    amenities = hotel_row['amenities'].split(';')
    tags = hotel_row['tags'].split(';')
    rule = season_rules.get(season_name, lambda h, t: 0.5)
    return rule(amenities, tags)

# =============================
# TÍNH TOÁN & XUẤT KẾT QUẢ
# =============================
results = []
for _, h in hotels_df.iterrows():
    s_event = score_event(h, events_df, reference_date)
    s_weather = score_weather(h, current_weather['condition'])
    s_season = score_season(h, season)
    total = 0.4*s_event + 0.3*s_weather + 0.3*s_season
    results.append({
        'Hotel': h['name'],
        'Price': h['price'],
        'Stars': h['stars'],
        'Score_Event': round(s_event,3),
        'Score_Weather': round(s_weather,3),
        'Score_Season': round(s_season,3),
        'Total_Score': round(total,3)
    })

df_result = pd.DataFrame(results).sort_values(by='Total_Score', ascending=False)
print("🔹 Goi y khach san (Top 5):")
print(df_result.head(5).to_string(index=False))
