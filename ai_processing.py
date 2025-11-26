import cv2
import easyocr
from ultralytics import YOLO
import numpy as np
import os
import unicodedata

# --- CẤU HÌNH AI ---
MODEL_PATH = 'models/best.pt'
CONFIDENCE_THRESHOLD = 0.25
EXPECTED_CLASS_ID = 0
OCR_ALLOWLIST = '0123456789ABCDEFGHKLMNPRSTUVXYZ-.'
CROP_SAVE_DIR = 'cropped_plates'
os.makedirs(CROP_SAVE_DIR, exist_ok=True)

# --- BIẾN TOÀN CỤC CHO AI ---
model_yolo = None
reader_ocr = None
class_name_display = ""

# --- HÀM TẢI TÀI NGUYÊN ---


def load_resources(status_callback):
    global model_yolo, reader_ocr, class_name_display
    try:
        status_callback("Đang tải model YOLO...")
        model_yolo = YOLO(MODEL_PATH)

        if EXPECTED_CLASS_ID in model_yolo.names:
            class_name_display = model_yolo.names[EXPECTED_CLASS_ID]
        else:
            class_name_display = "LicensePlate"

        status_callback("Đang khởi tạo EasyOCR...")
        reader_ocr = easyocr.Reader(['en'], gpu=False)

        status_callback("Hệ thống AI sẵn sàng!")
        return True
    except Exception as e:
        status_callback(f"Lỗi khởi tạo AI: {str(e)}")
        return False

# --- HÀM CHUYỂN ĐỔI TIẾNG VIỆT CÓ DẤU -> KHÔNG DẤU ---


def remove_accents(input_str):
    """
    Chuyển đổi chuỗi có dấu thành không dấu an toàn.

    """
    if not input_str:
        return ""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

# --- HÀM OCR ---


def perform_ocr(plate_img):
    try:
        height, width = plate_img.shape[:2]
        if height < 50 or width < 100:
            scale = 3
            plate_img = cv2.resize(
                plate_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        gray_plate = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)

        # Xử lý ảnh: CLAHE + Threshold
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        equalized_img = clahe.apply(gray_plate)
        _, thresholded_img = cv2.threshold(
            equalized_img, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
        )

        results = reader_ocr.readtext(
            thresholded_img,
            detail=0,
            allowlist=OCR_ALLOWLIST,
            paragraph=False
        )

        if not results:
            return "Unknown"

        full_text = "".join(results).strip()
        final_text = full_text.replace(
            ".", "").replace("-", "").replace(" ", "")

        if len(final_text) < 3:
            return "Unknown"
        return final_text
    except Exception as e:
        print(f"Lỗi OCR: {e}")
        return "Error"

# --- HÀM XỬ LÝ FRAME ---


def process_frame_for_web(frame, query_callback):
    global model_yolo
    if model_yolo is None:
        return frame, "Model chưa tải", []

    results = model_yolo(frame, verbose=False)[0]

    img_result = frame.copy()
    final_message = "Không phát hiện biển số."
    detection_count = 0

    # Danh sách chứa thông tin chi tiết để gửi về web
    detected_info = []

    for box in results.boxes:
        cls_id = int(box.cls[0].item())
        conf = box.conf[0].item()

        if cls_id == EXPECTED_CLASS_ID and conf >= CONFIDENCE_THRESHOLD:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

            h, w, _ = frame.shape
            crop_y1, crop_y2 = max(0, y1-5), min(h, y2+5)
            crop_x1, crop_x2 = max(0, x1-5), min(w, x2+5)
            plate_crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]

            text_ocr = "Unknown"
            owner_info = None

            if plate_crop.size > 0:
                text_ocr = perform_ocr(plate_crop)
                text_ocr, owner_info = query_callback(text_ocr)

                # Thêm thông tin vào danh sách
                detected_info.append({
                    'plate': text_ocr,
                    'owner': owner_info if owner_info else "Không có thông tin"
                })

            img_result = draw_results_for_web(
                img_result,
                (x1, y1, x2, y2),
                text_ocr,
                owner_info
            )
            detection_count += 1

    if detection_count > 0:
        final_message = f"Phát hiện {detection_count} biển số."

    # Trả về thêm detected_info
    return img_result, final_message, detected_info

# --- HÀM VẼ KẾT QUẢ (Đơn giản hóa, dùng cv2.putText) ---


def draw_results_for_web(img, bbox, plate_text, owner_text):
    x1, y1, x2, y2 = bbox

    # 1. Vẽ khung chữ nhật xanh lá
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # 2. Vẽ BIỂN SỐ
    (w_plate, h_plate), _ = cv2.getTextSize(
        plate_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
    cv2.rectangle(img, (x1, y1 - 40), (x1 + w_plate + 20, y1), (0, 255, 0), -1)
    cv2.putText(img, plate_text, (x1 + 5, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    # 3. Vẽ CHỦ XE (Nếu có)
    if owner_text:
        # Chuyển thành không dấu trước khi vẽ để tránh lỗi
        clean_owner_text = remove_accents(owner_text)

        # Tính toán kích thước khung nền
        # Font scale 0.6, độ dày 2
        (w_owner, h_owner), _ = cv2.getTextSize(
            clean_owner_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)

        # Vẽ nền màu cam bên dưới biển số
        y_bg_top = y2 + 5
        y_bg_bot = y2 + h_owner + 20

        cv2.rectangle(img, (x1, y_bg_top), (x1 + w_owner +
                      10, y_bg_bot), (255, 180, 0), -1)

        # Viết chữ đen lên nền cam
        cv2.putText(img, clean_owner_text, (x1 + 5, y2 + h_owner + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    return img
