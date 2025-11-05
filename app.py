import pandas as pd
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import re
from datetime import datetime
from flask_mail import Mail, Message  # thêm thư viện mail
import tempfile
from flask import session, flash

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# 📁 Đường dẫn đến các file dữ liệu
DATA_FOLDER = os.path.join(os.getcwd(), 'data')
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

HOTELS_CSV = os.path.join(DATA_FOLDER, 'hotels.csv')
BOOKINGS_CSV = os.path.join(DATA_FOLDER, 'bookings.csv')
# === CẤU HÌNH EMAIL ===
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USE_SSL=False,
    MAIL_USERNAME='hotelpinder@gmail.com',   # Gmail thật
    MAIL_PASSWORD='znsj ynpd burr tdeo',     # Mật khẩu ứng dụng 16 ký tự
    MAIL_DEFAULT_SENDER=('Hotel Pinder', 'hotelpinder@gmail.com')
)

mail = Mail(app)


# === FILE PATHS (CHỐNG PermissionError) ===
try:
    safe_dir = os.path.join(os.getcwd(), "data")
    os.makedirs(safe_dir, exist_ok=True)
    BOOKINGS_CSV = os.path.join(safe_dir, "bookings.csv")
    if not os.path.exists(BOOKINGS_CSV):
        df_empty = pd.DataFrame(columns=[
            "hotel_name", "room_type", "price", "user_name", "phone", "email",
            "num_adults", "num_children", "checkin_date", "nights",
            "special_requests", "booking_time"
        ])
        df_empty.to_csv(BOOKINGS_CSV, index=False, encoding="utf-8-sig")
except Exception as e:
    temp_dir = tempfile.gettempdir()
    BOOKINGS_CSV = os.path.join(temp_dir, "bookings.csv")
    print(f"[⚠] Không thể ghi vào thư mục chính, dùng tạm: {BOOKINGS_CSV}")

HOTELS_CSV = "hotels.csv"
REVIEWS_CSV = "reviews.csv"


# === ĐẢM BẢO FILE TỒN TẠI ===
if not os.path.exists(HOTELS_CSV):
    raise FileNotFoundError("❌ Không tìm thấy hotels.csv — hãy thêm file này trước!")

if not os.path.exists(REVIEWS_CSV):
    pd.DataFrame(columns=["hotel_name", "user", "rating", "comment"]).to_csv(
        REVIEWS_CSV, index=False, encoding="utf-8-sig"
    )


# === HÀM ĐỌC CSV AN TOÀN ===
def read_csv_safe(file_path):
    encodings = ["utf-8-sig", "utf-8", "cp1252"]
    for enc in encodings:
        try:
            df = pd.read_csv(file_path, encoding=enc, dtype=str)
            df.columns = df.columns.str.strip()
            numeric_cols = ['price', 'stars', 'rating', 'num_adults', 'num_children', 'nights']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = df[col].str.replace(',', '').astype(float)
            return df
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"⚠️ Lỗi khi xử lý file {file_path}: {e}")
            raise
    raise UnicodeDecodeError(f"Không đọc được file {file_path} với UTF-8 hoặc cp1252!")


# === LOAD DỮ LIỆU ===
hotels = read_csv_safe(HOTELS_CSV)
reviews_df = read_csv_safe(REVIEWS_CSV)

if 'name' not in hotels.columns:
    if 'Name' in hotels.columns:
        hotels = hotels.rename(columns={'Name': 'name'})
    else:
        raise KeyError("❌ hotels.csv không có cột 'name'!")

if 'hotel_name' not in reviews_df.columns:
    raise KeyError("❌ reviews.csv không có cột 'hotel_name'.")


# === HÀM PHỤ ===
def yes_no_icon(val):
    return "✅" if str(val).lower() in ("true", "1", "yes") else "❌"


def map_hotel_row(row):
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


# === TRANG CHỦ ===
@app.route('/')
def home():
    cities = sorted(hotels['city'].dropna().unique())
    return render_template('index.html', cities=cities)


# === TRANG GỢI Ý ===
@app.route('/recommend', methods=['POST', 'GET'])
def recommend():
    filtered = hotels.copy()

    if request.method == 'POST':
        city = request.form.get('location', '').lower()
        budget = request.form.get('budget', '')
        stars = request.form.get('stars', '')
    else:
        city = request.args.get('location', '').lower()
        budget = request.args.get('budget', '')
        stars = request.args.get('stars', '')

    if city:
        filtered = filtered[filtered['city'].str.lower() == city]

    if budget:
        try:
            budget = float(budget)
            filtered = filtered[filtered['price'] <= budget]
        except ValueError:
            pass

    if stars:
        try:
            stars = int(stars)
            filtered = filtered[filtered['stars'] >= stars]
        except ValueError:
            pass

    results = [map_hotel_row(r) for r in filtered.to_dict(orient='records')]
    return render_template('result.html', hotels=results)


# === TRANG CHI TIẾT ===
@app.route('/hotel/<name>')
def hotel_detail(name):
    hotel_data = hotels[hotels['name'] == name]
    if hotel_data.empty:
        return "<h3>Không tìm thấy khách sạn!</h3>", 404

    hotel = map_hotel_row(hotel_data.iloc[0].to_dict())
    reviews_df_local = read_csv_safe(REVIEWS_CSV)
    hotel_reviews = reviews_df_local[reviews_df_local['hotel_name'] == name].to_dict(orient='records')

    avg_rating = (
        round(sum(int(r['rating']) for r in hotel_reviews) / len(hotel_reviews), 1)
        if hotel_reviews else hotel.get('rating', 'Chưa có')
    )

    features = {
        "Buffet": yes_no_icon(hotel.get("buffet")),
        "Bể bơi": yes_no_icon(hotel.get("pool")),
        "Gần biển": yes_no_icon(hotel.get("sea_view") or hotel.get("sea")),
        "View biển": yes_no_icon(hotel.get("view")),
    }

    rooms = [
        {"type": "Phòng nhỏ", "price": round(float(hotel.get('price', 0)) * 1.0)},
        {"type": "Phòng đôi", "price": round(float(hotel.get('price', 0)) * 1.5)},
        {"type": "Phòng tổng thống", "price": round(float(hotel.get('price', 0)) * 2.5)},
    ]

    return render_template('detail.html', hotel=hotel, features=features, rooms=rooms,
                           reviews=hotel_reviews, avg_rating=avg_rating)


# === GỬI ĐÁNH GIÁ ===
@app.route('/review/<name>', methods=['POST'])
def add_review(name):
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

    return redirect(url_for('hotel_detail', name=name))


# === TRANG ĐẶT PHÒNG ===
@app.route('/booking/<name>/<room_type>', methods=['GET', 'POST'])
def booking(name, room_type):
    # Đọc dữ liệu khách sạn
    df_hotels = pd.read_csv(HOTELS_CSV, encoding='utf-8-sig')
    df_hotels.columns = df_hotels.columns.str.strip()
    df_hotels['name'] = df_hotels['name'].astype(str).str.strip()

    # Tìm khách sạn theo tên (không phân biệt hoa thường)
    match = df_hotels[df_hotels['name'].str.lower() == name.lower()]
    if match.empty:
        flash("Không tìm thấy khách sạn!", "danger")
        return redirect(url_for('home'))

    idx = match.index[0]
    hotel = map_hotel_row(match.iloc[0].to_dict())

    # Lấy số phòng còn lại
    rooms_left = int(df_hotels.at[idx, 'rooms_available'])

    if request.method == 'POST':
        # ====== Nếu đã hết phòng, chặn đặt ======
        if rooms_left <= 0:
            flash("Xin lỗi, khách sạn này đã hết phòng!", "warning")
            return redirect(url_for('hotel_detail', name=name))

        # ====== Lưu thông tin đặt phòng ======
        info = {
            "hotel_name": name,
            "room_type": room_type,
            "price": float(request.form.get('price', hotel.get('price', 0))),
            "user_name": request.form['fullname'],
            "phone": request.form['phone'],
            "email": request.form.get('email', ''),
            "num_adults": int(request.form.get('adults', 1)),
            "num_children": int(request.form.get('children', 0)),
            "checkin_date": request.form['checkin'],
            "nights": 1,
            "special_requests": request.form.get('note', ''),
            "booking_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "Chờ xác nhận"
        }

        # ====== Trừ số phòng & cập nhật trạng thái ======
        df_hotels.at[idx, 'rooms_available'] = max(rooms_left - 1, 0)
        df_hotels.at[idx, 'status'] = 'còn' if rooms_left - 1 > 0 else 'hết'

        df_hotels.to_csv(HOTELS_CSV, index=False, encoding='utf-8-sig')

        # ====== Ghi vào bookings.csv ======
        try:
            df_bookings = pd.read_csv(BOOKINGS_CSV, encoding='utf-8-sig')
        except FileNotFoundError:
            df_bookings = pd.DataFrame(columns=info.keys())

        df_bookings = pd.concat([df_bookings, pd.DataFrame([info])], ignore_index=True)
        df_bookings.to_csv(BOOKINGS_CSV, index=False, encoding='utf-8-sig')

        # ====== Gửi email xác nhận ======
        if info["email"]:
            try:
                msg_user = Message(
                    subject="Xác nhận đặt phòng - Hotel Pinder",
                    recipients=[info["email"]]
                )
                msg_user.html = f"""
                <div style='font-family: Arial, sans-serif;'>
                    <h2>Cảm ơn {info['user_name']}!</h2>
                    <p>Bạn đã đặt phòng <b>{info['room_type']}</b> tại <b>{info['hotel_name']}</b>.</p>
                    <p>Ngày nhận phòng: {info['checkin_date']}</p>
                    <p>Giá: {info['price']:,} VND</p>
                    <p>Số người: {info['num_adults']} NL, {info['num_children']} TE</p>
                    <p>Yêu cầu đặc biệt: {info['special_requests'] or 'Không có'}</p>
                </div>
                """
                mail.send(msg_user)
            except Exception as e:
                print(f"⚠️ Lỗi gửi email: {e}")

        flash(f"🎉 Đặt phòng tại {name} thành công! (Còn lại {max(rooms_left-1, 0)} phòng)", "success")
        return render_template('success.html', info=info)

    return render_template('booking.html', hotel=hotel, room_type=room_type)


    # ======= METHOD GET =======
    return render_template('booking.html', hotel=hotel, room_type=room_type)

# === LỊCH SỬ ĐẶT PHÒNG ===
@app.route('/history', methods=['GET', 'POST'])
def booking_history():
    bookings = []
    email = ""

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if os.path.exists(BOOKINGS_CSV) and email:
            df = pd.read_csv(BOOKINGS_CSV, encoding="utf-8-sig")
            df['email'] = df['email'].astype(str).str.lower()
            bookings = df[df['email'] == email].to_dict(orient='records')

    return render_template('history.html', bookings=bookings, email=email)


# === TRANG GIỚI THIỆU ===
@app.route('/about')
def about_page():
    return render_template('about.html')

from flask import session, flash

# === ĐĂNG NHẬP QUẢN TRỊ ===
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        # ⚙️ Tài khoản admin cố định (có thể sửa)
        if username == "admin" and password == "123456":
            session['admin'] = True
            flash("Đăng nhập thành công!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Sai tài khoản hoặc mật khẩu!", "danger")
    return render_template('admin_login.html')


# === ĐĂNG XUẤT ===
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash("Đã đăng xuất!", "info")
    return redirect(url_for('admin_login'))


# === TRANG DASHBOARD QUẢN TRỊ ===
@app.route('/admin')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    # Đọc dữ liệu
    hotels_df = pd.read_csv(HOTELS_CSV, encoding='utf-8-sig')
    bookings_df = pd.read_csv(BOOKINGS_CSV, encoding='utf-8-sig') if os.path.exists(BOOKINGS_CSV) else pd.DataFrame()

    total_hotels = len(hotels_df)
    total_bookings = len(bookings_df)
    total_cities = hotels_df['city'].nunique()

    return render_template('admin_dashboard.html',
                           total_hotels=total_hotels,
                           total_bookings=total_bookings,
                           total_cities=total_cities)


# === QUẢN LÝ KHÁCH SẠN ===
@app.route('/admin/hotels', methods=['GET', 'POST'])
def admin_hotels():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    df = pd.read_csv(HOTELS_CSV, encoding='utf-8-sig')

    # Thêm khách sạn mới
    if request.method == 'POST' and 'add_hotel' in request.form:
        name = request.form.get('name', '').strip()
        city = request.form.get('city', '').strip()
        price = request.form.get('price', '').strip()
        stars = request.form.get('stars', '').strip()
        description = request.form.get('description', '').strip()
        rooms_available = int(request.form.get('rooms_available', 1))
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
            df.to_csv(HOTELS_CSV, index=False, encoding="utf-8-sig")
            flash("Đã thêm khách sạn mới!", "success")
        else:
            flash("Tên và thành phố không được để trống!", "warning")

    # Cập nhật số phòng đã có
    if request.method == 'POST' and 'update_hotel' in request.form:
        name = request.form.get('update_name', '').strip()
        rooms_str = request.form.get('update_rooms', '0').strip()

    # Chuẩn hóa header và dữ liệu
        df.columns = df.columns.str.replace('\ufeff', '').str.strip().str.lower()
        df['name'] = df['name'].astype(str).str.strip().str.replace('\ufeff', '').str.lower()

        if name:
            clean_name = name.strip().lower()

        # ✅ Fix 1: chuyển đổi chuỗi sang số an toàn (cho cả "10", "10.0", " 10 ")
            try:
                rooms_available = int(float(rooms_str))
                if rooms_available < 0:
                    rooms_available = 0
            except:
                rooms_available = 0

        # ✅ Fix 2: so sánh tên khách sạn chính xác hơn
            mask = df['name'] == clean_name
            if mask.any():
            # ✅ Fix 3: cập nhật đúng cột, đảm bảo đồng bộ trạng thái
                df.loc[mask, 'rooms_available'] = rooms_available
                df.loc[mask, 'status'] = 'còn' if rooms_available > 0 else 'hết'

            # ✅ Fix 4: lưu UTF-8-sig để không lỗi BOM, giúp phần booking đọc được chính xác
                df.to_csv(HOTELS_CSV, index=False, encoding='utf-8-sig')

                flash(f"Đã cập nhật số phòng cho {name}", "success")
            else:
                flash(f"Không tìm thấy khách sạn {name}", "warning")
        else:
            flash("Thiếu tên khách sạn!", "danger")

# Chuyển đổi dataframe sang danh sách để render
    hotels = df.to_dict(orient='records')
    return render_template('admin_hotels.html', hotels=hotels)



# === Quản lý đặt phòng (Admin) ===
@app.route('/admin/bookings')
def admin_bookings():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    if os.path.exists(BOOKINGS_CSV):
        df = pd.read_csv(BOOKINGS_CSV, encoding='utf-8-sig')
        bookings = df.to_dict(orient='records')
    else:
        bookings = []

    return render_template('admin_bookings.html', bookings=bookings)


# === Xác nhận đặt phòng ===
@app.route('/admin/bookings/confirm/<booking_time>')
def admin_confirm_booking(booking_time):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    df = pd.read_csv(BOOKINGS_CSV, encoding='utf-8-sig')
    df.loc[df['booking_time'] == booking_time, 'status'] = 'Đã xác nhận'
    df.to_csv(BOOKINGS_CSV, index=False, encoding='utf-8-sig')
    flash("Đã xác nhận đặt phòng!", "success")
    return redirect(url_for('admin_bookings'))


# === Xóa đặt phòng ===
@app.route('/admin/bookings/delete/<booking_time>')
def admin_delete_booking(booking_time):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    df = pd.read_csv(BOOKINGS_CSV, encoding='utf-8-sig')
    df = df[df['booking_time'] != booking_time]
    df.to_csv(BOOKINGS_CSV, index=False, encoding='utf-8-sig')
    flash("Đã xóa đặt phòng!", "info")
    return redirect(url_for('admin_bookings'))


# === XÓA KHÁCH SẠN ===
@app.route('/admin/hotels/delete/<name>')
def delete_hotel(name):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    try:
        df = pd.read_csv(HOTELS_CSV, encoding='utf-8-sig')
        df = df[df['name'] != name]
        df.to_csv(HOTELS_CSV, index=False, encoding='utf-8-sig')
        flash(f"Đã xóa khách sạn: {name}", "info")
    except Exception as e:
        flash(f"Lỗi khi xóa khách sạn: {e}", "danger")
    return redirect(url_for('admin_hotels'))


# === CẬP NHẬT TRẠNG THÁI KHÁCH SẠN ===
@app.route('/admin/hotels/status/<name>/<status>')
def update_hotel_status(name, status):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    try:
        df = pd.read_csv(HOTELS_CSV, encoding='utf-8-sig')
        if name in df['name'].values:
            df.loc[df['name'] == name, 'status'] = status
            df.to_csv(HOTELS_CSV, index=False, encoding='utf-8-sig')
            flash(f"Đã cập nhật {name} → {status}", "success")
    except Exception as e:
        flash(f"Lỗi khi cập nhật trạng thái: {e}", "danger")
    return redirect(url_for('admin_hotels'))


# === KHỞI CHẠY APP ===
if __name__ == '__main__':
    app.run(debug=True)


