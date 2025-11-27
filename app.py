from flask import (
    Flask, request, render_template, jsonify, redirect,
    url_for, session, send_from_directory
)
import os
import cv2
import numpy as np
import uuid
import gc
from dotenv import load_dotenv

os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
np.seterr(all='ignore')

from ai_processing import load_resources, process_frame_for_web
import db_utils

load_dotenv()

app = Flask(__name__)
# Lấy khóa bí mật từ file .env để quản lý session
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
app.config['UPLOAD_FOLDER'] = 'static/results'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- TẢI MODEL AI KHI KHỞI ĐỘNG SERVER ---
print("Đang khởi tạo hệ thống AI...")
load_resources(print)
print("Hệ thống AI đã tải xong.")
# ----------------------------------------

# --- CÁC ROUTE (ĐƯỜNG DẪN) CỦA WEB ---

# --- Route Xác thực ---


@app.route('/')
def route_root():
    """Trang chủ, chuyển hướng đến login nếu chưa đăng nhập."""
    if 'username' in session:
        return redirect(url_for('route_index'))
    return redirect(url_for('route_login'))


@app.route('/login', methods=['GET', 'POST'])
def route_login():
    if request.method == 'POST':
        data = request.json
        username = data.get('username')
        password = data.get('password')

        if db_utils.check_login(username, password):
            session['username'] = username  # Lưu session
            return jsonify({'success': True, 'message': 'Đăng nhập thành công!'})
        else:
            return jsonify({'success': False, 'message': 'Sai tên đăng nhập hoặc mật khẩu.'}), 401

    # Nếu là GET, chỉ hiển thị trang login
    return render_template('login.html')


@app.route('/register', methods=['POST'])
def route_register():
    data = request.json
    # Lấy dữ liệu...
    username = data.get('username')
    password = data.get('password')
    owner_name = data.get('owner_name')
    phone = data.get('phone')
    license_plate = data.get('license_plate')
    vehicle_info = data.get('vehicle_info', '')

    # Validate
    if not all([username, password, owner_name, license_plate]):
        return jsonify({'success': False, 'message': 'Vui lòng điền các trường bắt buộc.'}), 400

    success, message = db_utils.register_user(
        username, password, owner_name, phone, license_plate, vehicle_info
    )

    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message}), 400


@app.route('/logout')
def route_logout():
    session.pop('username', None)
    return redirect(url_for('route_login'))

# --- Route Ứng dụng chính ---


@app.route('/app')
def route_index():
    """Hiển thị trang ứng dụng chính."""
    if 'username' not in session:
        return redirect(url_for('route_login'))

    # Truyền tên username vào template để chào
    return render_template('index.html', username=session.get('username'))


@app.route('/upload', methods=['POST'])
def route_upload():
    """Xử lý upload ảnh."""
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Chưa xác thực'}), 401

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Không có file nào'}), 400

    file = request.files['file']

    try:
        img_bytes = file.read()
        if len(img_bytes) > 10 * 1024 * 1024:
            return jsonify({'success': False, 'message': 'File quá lớn. Tối đa 10MB.'}), 400

        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({'success': False, 'message': 'File không phải là ảnh.'}), 400

        del img_bytes, nparr

        img_result, message, details = process_frame_for_web(
            img,
            db_utils.query_owner_info
        )

        filename = f"{uuid.uuid4()}.jpg"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        cv2.imwrite(save_path, img_result, [cv2.IMWRITE_JPEG_QUALITY, 85])

        del img, img_result

        # 4. Trả về JSON (Thêm field 'details')
        result_url = url_for('static', filename=f'results/{filename}')

        gc.collect()
        return jsonify({
            'success': True,
            'message': message,
            'result_url': result_url,
            'details': details
        })
    except Exception as e:
        print(f"Error: {e}")
        gc.collect()
        return jsonify({'success': False, 'message': f'Lỗi Server: {e}'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
