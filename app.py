import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import re
from datetime import datetime
from flask_mail import Mail, Message
import tempfile
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-123")

# ==================== CẤU HÌNH ĐƯỜNG DẪN FILE ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_FOLDER, exist_ok=True)

# Đường dẫn file CSV
HOTELS_CSV = os.path.join(BASE_DIR, 'hotels.csv')
REVIEWS_CSV = os.path.join(BASE_DIR, 'reviews.csv')
BOOKINGS_CSV = os.path.join(DATA_FOLDER, 'bookings.csv')

# ==================== CẤU HÌNH GEMINI AI ====================
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("✅ Gemini AI đã được kích hoạt")
else:
    print("⚠️ Chưa có Gemini API Key - AI sẽ trả về response mẫu")

def get_ai_response(message):
    """Gọi Gemini AI hoặc trả về response mẫu nếu không có API Key"""
    if not GEMINI_API_KEY:
        # Response mẫu khi không có API Key (để test)
        sample_responses = {
            "xin chào": "👋 Chào bạn! Tôi là AI trợ lý du lịch. Tôi có thể giúp bạn tìm khách sạn, so sánh giá, và tư vấn địa điểm!",
            "chào": "👋 Chào bạn! Tôi có thể giúp gì cho chuyến du lịch của bạn?",
            "tìm khách sạn": "🏨 Tuyệt vời! Tôi có thể giúp bạn tìm khách sạn. Bạn muốn ở thành phố nào? (Hà Nội, Đà Nẵng, Hồ Chí Minh)",
            "hà nội": "📍 Hà Nội có nhiều khách sạn tuyệt vời! Bạn có ngân sách bao nhiêu một đêm?",
            "đà nẵng": "🌊 Đà Nẵng là điểm đến tuyệt vời! Bạn cần khách sạn bao nhiêu sao?",
            "hồ chí minh": "🏙️ Sài Gòn nhộn nhịp! Bạn muốn khách sạn có hồ bơi không?",
            "giá rẻ": "💰 Tôi tìm thấy vài khách sạn giá tốt: Khách sạn A (800k), Khách sạn B (750k) - xem chi tiết trên website nhé!",
            "cảm ơn": "❤️ Không có chi! Chúc bạn có chuyến du lịch thật vui!",
            "help": "💡 Tôi có thể giúp bạn: Tìm khách sạn • So sánh giá • Tư vấn địa điểm • Đặt phòng",
        }
        
        # Tìm response phù hợp
        message_lower = message.lower()
        for key, response in sample_responses.items():
            if key in message_lower:
                return response
        
        return "🤖 Tôi là AI trợ lý du lịch. Hiện tôi có thể giúp bạn tìm khách sạn, so sánh giá cả, và tư vấn địa điểm du lịch. Bạn cần hỗ trợ gì ạ?"
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Bạn là 'Travel Buddy AI' - trợ lý du lịch thân thiện bằng tiếng Việt. 
        Giọng văn vui vẻ, gần gũi, sử dụng từ ngữ thân mật.
        Hãy trả lời câu hỏi về du lịch, khách sạn một cách nhiệt tình và hữu ích.
        
        Câu hỏi: {message}
        """
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"🤖 Xin lỗi, tôi đang gặp sự cố kỹ thuật: {str(e)}. Vui lòng thử lại sau!"

# ==================== API CHATBOT ====================
@app.route('/api/chat', methods=['POST'])
def handle_chat():
    """API xử lý tin nhắn chatbot"""
    try:
        data = request.json
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({'success': False, 'response': 'Vui lòng nhập tin nhắn'})
        
        ai_response = get_ai_response(user_message)
        return jsonify({'success': True, 'response': ai_response})
        
    except Exception as e:
        return jsonify({'success': False, 'response': 'Lỗi hệ thống. Vui lòng thử lại!'})

# ==================== CẤU HÌNH EMAIL ====================
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USE_SSL=False,
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME', ''),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD', ''),
    MAIL_DEFAULT_SENDER=('Hotel Pinder', 'hotelpinder@gmail.com')
)
mail = Mail(app)

# ==================== KHỞI TẠO FILE ====================
def initialize_files():
    global BOOKINGS_CSV
    try:
        # Tạo file bookings nếu chưa có
        if not os.path.exists(BOOKINGS_CSV):
            df_empty = pd.DataFrame(columns=[
                "hotel_name", "room_type", "price", "user_name", "phone", "email",
                "num_adults", "num_children", "checkin_date", "nights",
                "special_requests", "booking_time", "status"
            ])
            df_empty.to_csv(BOOKINGS_CSV, index=False, encoding="utf-8-sig")
            print("✅ Đã tạo file bookings.csv")

        # Tạo file reviews nếu chưa có
        if not os.path.exists(REVIEWS_CSV):
            pd.DataFrame(columns=["hotel_name", "user", "rating", "comment"]).to_csv(
                REVIEWS_CSV, index=False, encoding="utf-8-sig"
            )
            print("✅ Đã tạo file reviews.csv")

        # Kiểm tra file hotels.csv
        if not os.path.exists(HOTELS_CSV):
            raise FileNotFoundError(f"❌ Không tìm thấy hotels.csv — đặt file ở: {HOTELS_CSV}")

    except Exception as e:
        print(f"⚠️ Lỗi khi khởi tạo file: {e}")
        # Fallback đến thư mục tạm
        temp_dir = tempfile.gettempdir()
        BOOKINGS_CSV = os.path.join(temp_dir, "bookings.csv")

# Gọi hàm khởi tạo
initialize_files()

# ==================== HÀM HỖ TRỢ ====================
def read_csv_safe(file_path):
    """Đọc CSV an toàn với nhiều encoding"""
    encodings = ["utf-8-sig", "utf-8", "cp1252"]
    for enc in encodings:
        try:
            df = pd.read_csv(file_path, encoding=enc, dtype=str)
            df.columns = df.columns.str.strip()
            
            # Convert các cột số
            numeric_cols = ['price', 'stars', 'rating', 'num_adults', 'num_children', 'nights', 'rooms_available']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(',', '').str.strip()
                    df[col] = df[col].str.replace(r'\.0$', '', regex=True)
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            return df
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"⚠️ Lỗi khi xử lý file {file_path}: {e}")
    raise UnicodeDecodeError(f"Không đọc được file {file_path}")

def yes_no_icon(val):
    """Chuyển giá trị boolean thành icon"""
    return "✅" if str(val).lower() in ("true", "1", "yes", "có") else "❌"

def map_hotel_row(row):
    """Chuẩn hóa dữ liệu khách sạn"""
    h = dict(row)
    h["image"] = h.get("image_url", h.get("image", ""))
    html_desc = h.get("review") or h.get("description") or ""
    h["full_desc"] = html_desc
    clean = re.sub(r'<[^>]*>', '', html_desc)
    h["short_desc"] = clean[:150] + ("..." if len(clean) > 150 else "")
    h["gym"] = h.get("gym", False)
    h["spa"] = h.get("spa", False)
    h["sea_view"] = h.get("sea") if "sea" in h else h.get("sea_view", False)
    return h

def ensure_hotel_columns(df):
    """Đảm bảo các cột cần thiết tồn tại"""
    if 'rooms_available' not in df.columns:
        df['rooms_available'] = 0
    df['rooms_available'] = df['rooms_available'].astype(int)
    
    if 'status' not in df.columns:
        df['status'] = df['rooms_available'].apply(lambda x: 'còn' if int(x) > 0 else 'hết')
    else:
        df['status'] = df['rooms_available'].apply(lambda x: 'còn' if int(x) > 0 else 'hết')
    
    return df

# ==================== ROUTES CHÍNH ====================
@app.route('/')
def home():
    """Trang chủ"""
    try:
        hotels_df = read_csv_safe(HOTELS_CSV)
        hotels_df = ensure_hotel_columns(hotels_df)
        cities = sorted(hotels_df['city'].dropna().unique())
        return render_template('index.html', cities=cities)
    except Exception as e:
        return f"<h3>Lỗi tải dữ liệu: {str(e)}</h3>", 500

@app.route('/recommend', methods=['POST', 'GET'])
def recommend():
    """Trang gợi ý khách sạn"""
    try:
        filtered = read_csv_safe(HOTELS_CSV)
        filtered = ensure_hotel_columns(filtered)

        if request.method == 'POST':
            city = request.form.get('location', '').lower()
            budget = request.form.get('budget', '')
            stars = request.form.get('stars', '')
        else:
            city = request.args.get('location', '').lower()
            budget = request.args.get('budget', '')
            stars = request.args.get('stars', '')

        # Lọc theo thành phố
        if city:
            filtered = filtered[filtered['city'].str.lower() == city]

        # Lọc theo ngân sách
        if budget:
            try:
                budget = float(budget)
                filtered = filtered[filtered['price'] <= budget]
            except Exception:
                pass

        # Lọc theo số sao
        if stars:
            try:
                stars = int(stars)
                filtered = filtered[filtered['stars'] >= stars]
            except Exception:
                pass

        results = [map_hotel_row(r) for r in filtered.to_dict(orient='records')]
        return render_template('result.html', hotels=results)
    
    except Exception as e:
        flash(f"Lỗi khi tìm kiếm: {str(e)}", "danger")
        return redirect(url_for('home'))

@app.route('/hotel/<name>')
def hotel_detail(name):
    """Trang chi tiết khách sạn"""
    try:
        hotels_df = read_csv_safe(HOTELS_CSV)
        hotels_df = ensure_hotel_columns(hotels_df)

        hotel_data = hotels_df[hotels_df['name'] == name]

        if hotel_data.empty:
            flash("Không tìm thấy khách sạn!", "danger")
            return redirect(url_for('home'))

        hotel = map_hotel_row(hotel_data.iloc[0].to_dict())
        reviews_df_local = read_csv_safe(REVIEWS_CSV)
        hotel_reviews = reviews_df_local[reviews_df_local['hotel_name'] == name].to_dict(orient='records')

        # Tính rating trung bình
        avg_rating = (
            round(sum(float(r.get('rating', 0)) for r in hotel_reviews) / len(hotel_reviews), 1)
            if hotel_reviews else hotel.get('rating', 'Chưa có')
        )

        # Tính năng khách sạn
        features = {
            "Buffet sáng": yes_no_icon(hotel.get("buffet")),
            "Bể bơi": yes_no_icon(hotel.get("pool")),
            "Phòng gym": yes_no_icon(hotel.get("gym")),
            "Spa": yes_no_icon(hotel.get("spa")),
            "View biển": yes_no_icon(hotel.get("sea_view") or hotel.get("sea")),
        }

        # Loại phòng
        rooms = [
            {"type": "Phòng Tiêu Chuẩn", "price": round(float(hotel.get('price', 0)) * 1.0)},
            {"type": "Phòng Superior", "price": round(float(hotel.get('price', 0)) * 1.3)},
            {"type": "Phòng Deluxe", "price": round(float(hotel.get('price', 0)) * 1.6)},
            {"type": "Suite", "price": round(float(hotel.get('price', 0)) * 2.0)},
        ]

        return render_template('detail.html', hotel=hotel, features=features, rooms=rooms,
                               reviews=hotel_reviews, avg_rating=avg_rating)
    
    except Exception as e:
        flash(f"Lỗi tải chi tiết khách sạn: {str(e)}", "danger")
        return redirect(url_for('home'))

@app.route('/review/<name>', methods=['POST'])
def add_review(name):
    """Thêm đánh giá khách sạn"""
    try:
        user = request.form.get('user', 'Ẩn danh').strip()
        rating = int(request.form.get('rating', 0))
        comment = request.form.get('comment', '').strip()

        new_review = pd.DataFrame([{
            "hotel_name": name,
            "user": user,
            "rating": rating,
            "comment": comment
        }])

        df = read_csv_safe(REVIEWS_CSV)
        df = pd.concat([df, new_review], ignore_index=True)
        df.to_csv(REVIEWS_CSV, index=False, encoding="utf-8-sig")

        flash("✅ Đã gửi đánh giá thành công!", "success")
        return redirect(url_for('hotel_detail', name=name))
    
    except Exception as e:
        flash(f"Lỗi khi gửi đánh giá: {str(e)}", "danger")
        return redirect(url_for('hotel_detail', name=name))

@app.route('/booking/<name>/<room_type>', methods=['GET', 'POST'])
def booking(name, room_type):
    """Trang đặt phòng"""
    try:
        hotels_df = read_csv_safe(HOTELS_CSV)
        hotels_df = ensure_hotel_columns(hotels_df)

        hotel_data = hotels_df[hotels_df['name'] == name]

        if hotel_data.empty:
            flash("Không tìm thấy khách sạn!", "danger")
            return redirect(url_for('home'))

        hotel = map_hotel_row(hotel_data.iloc[0].to_dict())
        
        # Kiểm tra phòng còn trống
        is_available = hotel['status'].lower() == 'còn'
        if not is_available:
            flash("⚠️ Khách sạn này hiện đã hết phòng. Vui lòng chọn khách sạn khác.", "warning")

        if request.method == 'POST':
            info = {
                "hotel_name": name,
                "room_type": room_type,
                "price": float(request.form.get('price', hotel.get('price', 0))),
                "user_name": request.form['fullname'].strip(),
                "phone": request.form['phone'].strip(),
                "email": request.form.get('email', '').strip(),
                "num_adults": max(int(request.form.get('adults', 1)), 1),
                "num_children": max(int(request.form.get('children', 0)), 0),
                "checkin_date": request.form['checkin'],
                "nights": max(int(request.form.get('nights', 1)), 1),
                "special_requests": request.form.get('note', '').strip(),
                "booking_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "Chờ xác nhận"
            }

            # Lưu booking
            try:
                df = pd.read_csv(BOOKINGS_CSV, encoding="utf-8-sig")
            except FileNotFoundError:
                df = pd.DataFrame(columns=info.keys())
            
            df = pd.concat([df, pd.DataFrame([info])], ignore_index=True)
            df.to_csv(BOOKINGS_CSV, index=False, encoding="utf-8-sig")

            # Gửi email xác nhận
            if info["email"]:
                try:
                    msg_user = Message(
                        subject="Xác nhận đặt phòng - Hotel Pinder",
                        recipients=[info["email"]]
                    )
                    msg_user.html = f"""
                    <h2>✅ Đặt phòng thành công!</h2>
                    <p><strong>Khách sạn:</strong> {info['hotel_name']}</p>
                    <p><strong>Loại phòng:</strong> {info['room_type']}</p>
                    <p><strong>Ngày nhận phòng:</strong> {info['checkin_date']}</p>
                    <p><strong>Số đêm:</strong> {info['nights']}</p>
                    <p><strong>Tổng tiền:</strong> {info['price']:,.0f} VND</p>
                    <p><strong>Trạng thái:</strong> {info['status']}</p>
                    <br>
                    <p>Cảm ơn bạn đã sử dụng dịch vụ của chúng tôi!</p>
                    """
                    mail.send(msg_user)
                except Exception as e:
                    print(f"⚠️ Lỗi gửi email cho khách: {e}")

            flash("✅ Đặt phòng thành công! Vui lòng kiểm tra email để xác nhận.", "success")
            return render_template('success.html', info=info)

        return render_template('booking.html', hotel=hotel, room_type=room_type, is_available=is_available)
    
    except Exception as e:
        flash(f"Lỗi khi đặt phòng: {str(e)}", "danger")
        return redirect(url_for('home'))

@app.route('/history', methods=['GET', 'POST'])
def booking_history():
    """Lịch sử đặt phòng"""
    bookings = []
    email = ""

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if os.path.exists(BOOKINGS_CSV) and email:
            try:
                df = pd.read_csv(BOOKINGS_CSV, encoding='utf-8-sig')
                df['email'] = df['email'].astype(str).str.lower()
                bookings = df[df['email'] == email].to_dict(orient='records')
                if not bookings:
                    flash("Không tìm thấy lịch sử đặt phòng cho email này!", "info")
            except Exception as e:
                flash(f"Lỗi khi đọc lịch sử: {str(e)}", "danger")

    return render_template('history.html', bookings=bookings, email=email)

@app.route('/about')
def about_page():
    """Trang giới thiệu"""
    return render_template('about.html')

# ==================== ROUTES QUẢN TRỊ ====================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Đăng nhập admin"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if username == "admin" and password == "123456":
            session['admin'] = True
            flash("Đăng nhập thành công!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Sai tài khoản hoặc mật khẩu!", "danger")
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """Đăng xuất admin"""
    session.pop('admin', None)
    flash("Đã đăng xuất!", "info")
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin_dashboard():
    """Dashboard quản trị"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    try:
        hotels_df = pd.read_csv(HOTELS_CSV, encoding='utf-8-sig')
        bookings_df = pd.read_csv(BOOKINGS_CSV, encoding='utf-8-sig') if os.path.exists(BOOKINGS_CSV) else pd.DataFrame()

        total_hotels = len(hotels_df)
        total_bookings = len(bookings_df)
        total_cities = hotels_df['city'].nunique()
        pending_bookings = len(bookings_df[bookings_df['status'] == 'Chờ xác nhận']) if not bookings_df.empty else 0

        return render_template('admin_dashboard.html',
                               total_hotels=total_hotels,
                               total_bookings=total_bookings,
                               total_cities=total_cities,
                               pending_bookings=pending_bookings)
    
    except Exception as e:
        flash(f"Lỗi tải dashboard: {str(e)}", "danger")
        return render_template('admin_dashboard.html',
                               total_hotels=0,
                               total_bookings=0,
                               total_cities=0,
                               pending_bookings=0)

@app.route('/admin/hotels', methods=['GET', 'POST'])
def admin_hotels():
    """Quản lý khách sạn"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    try:
        df = pd.read_csv(HOTELS_CSV, encoding='utf-8-sig')
        df = ensure_hotel_columns(df)

        # Thêm khách sạn mới
        if request.method == 'POST' and 'name' in request.form:
            name = request.form.get('name', '').strip()
            city = request.form.get('city', '').strip()
            price = request.form.get('price', '0').strip()
            stars = request.form.get('stars', '3').strip()
            description = request.form.get('description', '').strip()
            rooms_available = request.form.get('rooms_available', '1')

            try:
                rooms_available = int(float(str(rooms_available).replace(',', '').replace('.0', '')))
            except Exception:
                rooms_available = 1

            if name and city:
                new_row = {
                    "name": name,
                    "city": city,
                    "price": price,
                    "stars": stars,
                    "description": description,
                    "rooms_available": rooms_available,
                    "status": "còn" if rooms_available > 0 else "hết"
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(HOTELS_CSV, index=False, encoding='utf-8-sig')
                flash("✅ Đã thêm khách sạn mới!", "success")
                return redirect(url_for('admin_hotels'))
            else:
                flash("⚠️ Tên và thành phố không được để trống!", "warning")

        # Cập nhật số phòng
        if request.method == 'POST' and 'update_rooms' in request.form:
            update_name = request.form.get('update_name', '').strip()
            update_rooms = request.form.get('update_rooms', '').strip()

            try:
                update_rooms = int(float(str(update_rooms).replace(',', '').replace('.0', '')))
            except ValueError:
                update_rooms = 0

            if update_name in df['name'].values:
                df.loc[df['name'] == update_name, 'rooms_available'] = update_rooms
                df.loc[df['name'] == update_name, 'status'] = 'còn' if update_rooms > 0 else 'hết'
                df.to_csv(HOTELS_CSV, index=False, encoding='utf-8-sig')
                flash(f"🔧 Đã cập nhật số phòng cho {update_name}", "success")
            else:
                flash("⚠️ Không tìm thấy khách sạn có tên này!", "danger")

        hotels = df.to_dict(orient='records')
        return render_template('admin_hotels.html', hotels=hotels)
    
    except Exception as e:
        flash(f"Lỗi quản lý khách sạn: {str(e)}", "danger")
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/bookings')
def admin_bookings():
    """Quản lý đặt phòng"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    try:
        if os.path.exists(BOOKINGS_CSV):
            df = pd.read_csv(BOOKINGS_CSV, encoding='utf-8-sig')
            bookings = df.to_dict(orient='records')
        else:
            bookings = []

        return render_template('admin_bookings.html', bookings=bookings)
    
    except Exception as e:
        flash(f"Lỗi tải danh sách đặt phòng: {str(e)}", "danger")
        return render_template('admin_bookings.html', bookings=[])

@app.route('/admin/bookings/confirm/<booking_time>')
def admin_confirm_booking(booking_time):
    """Xác nhận đặt phòng"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    try:
        df = pd.read_csv(BOOKINGS_CSV, encoding='utf-8-sig')
        df.loc[df['booking_time'] == booking_time, 'status'] = 'Đã xác nhận'
        df.to_csv(BOOKINGS_CSV, index=False, encoding='utf-8-sig')
        flash("✅ Đã xác nhận đặt phòng!", "success")
    
    except Exception as e:
        flash(f"Lỗi khi xác nhận: {str(e)}", "danger")
    
    return redirect(url_for('admin_bookings'))

@app.route('/admin/bookings/delete/<booking_time>')
def admin_delete_booking(booking_time):
    """Xóa đặt phòng"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    try:
        df = pd.read_csv(BOOKINGS_CSV, encoding='utf-8-sig')
        df = df[df['booking_time'] != booking_time]
        df.to_csv(BOOKINGS_CSV, index=False, encoding='utf-8-sig')
        flash("🗑️ Đã xóa đặt phòng!", "info")
    
    except Exception as e:
        flash(f"Lỗi khi xóa: {str(e)}", "danger")
    
    return redirect(url_for('admin_bookings'))

@app.route('/admin/hotels/delete/<name>')
def delete_hotel(name):
    """Xóa khách sạn"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    try:
        df = pd.read_csv(HOTELS_CSV, encoding='utf-8-sig')
        df = df[df['name'] != name]
        df.to_csv(HOTELS_CSV, index=False, encoding='utf-8-sig')
        flash(f"🗑️ Đã xóa khách sạn: {name}", "info")
    
    except Exception as e:
        flash(f"Lỗi khi xóa khách sạn: {e}", "danger")
    
    return redirect(url_for('admin_hotels'))

@app.route('/admin/hotels/status/<name>/<status>')
def update_hotel_status(name, status):
    """Cập nhật trạng thái khách sạn"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    try:
        df = pd.read_csv(HOTELS_CSV, encoding='utf-8-sig')

        if name in df['name'].values:
            df.loc[df['name'] == name, 'status'] = status

            # Đồng bộ rooms_available
            if status.strip().lower() == 'còn':
                df.loc[df['name'] == name, 'rooms_available'] = df.loc[df['name'] == name, 'rooms_available'].replace(0, 1)
            elif status.strip().lower() == 'hết':
                df.loc[df['name'] == name, 'rooms_available'] = 0

            df['status'] = df['rooms_available'].apply(lambda x: 'còn' if x > 0 else 'hết')
            df.to_csv(HOTELS_CSV, index=False, encoding='utf-8-sig')
            flash(f"✅ Đã cập nhật {name} → {status}", "success")
        else:
            flash("⚠️ Không tìm thấy khách sạn này!", "warning")
    
    except Exception as e:
        flash(f"Lỗi khi cập nhật trạng thái: {e}", "danger")
    
    return redirect(url_for('admin_hotels'))

# ==================== KHỞI CHẠY ỨNG DỤNG ====================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)




