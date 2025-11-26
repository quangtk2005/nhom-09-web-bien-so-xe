import firebase_admin
from firebase_admin import credentials, firestore
import bcrypt
from thefuzz import fuzz
import os

# --- KHỞI TẠO BIẾN TOÀN CỤC ---
db = None

# --- CẤU HÌNH FIREBASE ---


def initialize_firebase():
    global db
    try:
        if not firebase_admin._apps:
            firebase_cred = os.getenv('FIREBASE_CREDENTIALS')
            if firebase_cred:
                import json
                cred_dict = json.loads(firebase_cred)
                cred = credentials.Certificate(cred_dict)
            elif os.path.exists("firebase_key.json"):
                cred = credentials.Certificate("firebase_key.json")
            else:
                print("LỖI: Không tìm thấy Firebase credentials.")
                return
            
            firebase_admin.initialize_app(cred)

        db = firestore.client()
        print("✅ Kết nối Firebase thành công!")

    except Exception as e:
        print(f"❌ Lỗi khởi tạo Firebase: {e}")
        db = None


# Gọi hàm khởi tạo ngay khi import file
initialize_firebase()

# --- HÀM BẢO MẬT ---


def hash_password(password):
    salt = bcrypt.gensalt()
    pwd_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
    return pwd_hash.decode('utf-8')


def verify_password(stored_password_hash, provided_password):
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password_hash.encode('utf-8'))

# --- CÁC HÀM XỬ LÝ VỚI FIREBASE ---


def register_user(username, password, owner_name, phone, license_plate, vehicle_info):
    """Đăng ký user mới vào Collection 'users'."""
    global db

    if db is None:
        return False, "Lỗi hệ thống: Chưa kết nối được Database (Kiểm tra file key)."
    try:
        # 1. Kiểm tra xem username đã tồn tại chưa
        user_ref = db.collection('users').document(username)
        if user_ref.get().exists:
            return False, "Tên đăng nhập đã tồn tại."

        # 2. Kiểm tra biển số xe đã tồn tại chưa (Quét toàn bộ collection)
        existing_plates = db.collection('users').where(
            'license_plate', '==', license_plate.upper()).stream()
        for _ in existing_plates:
            return False, "Biển số xe đã được đăng ký bởi người khác."

        # 3. Lưu dữ liệu
        password_hash = hash_password(password)
        data = {
            'username': username,
            'password_hash': password_hash,
            'owner_name': owner_name,
            'phone': phone,
            'license_plate': license_plate.upper(),
            'vehicle_info': vehicle_info,
            'created_at': firestore.SERVER_TIMESTAMP
        }

        # Set dữ liệu vào document có ID là username
        user_ref.set(data)

        return True, "Đăng ký thành công!"

    except Exception as e:
        print(f"Lỗi Firebase Register: {e}")
        return False, f"Lỗi hệ thống: {e}"


def check_login(username, password):
    """Kiểm tra đăng nhập."""
    try:
        user_ref = db.collection('users').document(username)
        doc = user_ref.get()

        if doc.exists:
            user_data = doc.to_dict()
            stored_hash = user_data.get('password_hash')
            if verify_password(stored_hash, password):
                return True
        return False
    except Exception as e:
        print(f"Lỗi Firebase Login: {e}")
        return False


def query_owner_info(plate_text):
    """Truy vấn Fuzzy Matching trên Firebase."""
    if not plate_text or plate_text == "Unknown" or plate_text == "Error":
        return plate_text, None

    try:
        # 1. Lấy TẤT CẢ user về để so khớp
        users_ref = db.collection('users')
        docs = users_ref.stream()

        best_match_data = None
        best_score = 0

        # Chuẩn hóa biển số đầu vào
        clean_plate_text = plate_text.replace(
            ".", "").replace("-", "").replace(" ", "")

        for doc in docs:
            user_data = doc.to_dict()
            db_plate = user_data.get('license_plate', '')

            # Chuẩn hóa biển số trong DB
            clean_db_plate = db_plate.replace(
                ".", "").replace("-", "").replace(" ", "")

            # So khớp
            score = fuzz.ratio(clean_plate_text, clean_db_plate)

            if score > best_score:
                best_score = score
                best_match_data = user_data

        # 2. Quyết định (Ngưỡng 80%)
        MATCH_THRESHOLD = 80

        if best_score >= MATCH_THRESHOLD:
            print(
                f"Fuzzy Match: '{plate_text}' -> '{best_match_data['license_plate']}' ({best_score}%)")
            info = f"{best_match_data['owner_name']} ({best_match_data.get('phone', '')})"
            return best_match_data['license_plate'], info
        else:
            print(f"No Match: '{plate_text}' (Best: {best_score}%)")
            return plate_text, None

    except Exception as e:
        print(f"Lỗi Firebase Query: {e}")
        return plate_text, None


def close_db_conn(e=None):
    pass
