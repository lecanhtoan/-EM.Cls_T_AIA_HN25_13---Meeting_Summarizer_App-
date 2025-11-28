# Hướng dẫn cài đặt và chạy ứng dụng trên Windows

Tài liệu này hướng dẫn thiết lập môi trường và chạy Meeting Notes Summarizer trên Windows 10/11. Nội dung bao gồm: cài đặt PostgreSQL, Python, Node.js; cấu hình Azure OpenAI; khởi tạo database; chạy backend và frontend.

---

## 1) Yêu cầu hệ thống

- Windows 10/11 (64-bit)
- Quyền cài đặt phần mềm
- Kết nối Internet

---

## 2) Cài đặt phần mềm cần thiết

### 2.1 PostgreSQL
- Tải PostgreSQL Installer: https://www.postgresql.org/download/windows/
- Cài đặt PostgreSQL 14+ (hoặc 16) và pgAdmin (tùy chọn)
- Ghi nhớ mật khẩu user `postgres` bạn thiết lập trong quá trình cài đặt
- Sau khi cài, PostgreSQL service sẽ tự chạy

Tạo database `meeting_notes_summarizer`:
- Mở Command Prompt (CMD) hoặc PowerShell, chạy:
  ```bat
  psql -U postgres -c "CREATE DATABASE meeting_notes_summarizer;"
  ```
  Nhập mật khẩu postgres khi được yêu cầu.

### 2.2 Python 3.12+
- Tải Python: https://www.python.org/downloads/windows/
- Cài đặt Python 3.12+ và tick "Add Python to PATH"
- Kiểm tra:
  ```bat
  python --version
  ```

### 2.3 Node.js (LTS)
- Tải Node.js LTS: https://nodejs.org/en
- Cài đặt và kiểm tra:
  ```bat
  node -v
  npm -v
  ```

---

## 3) Lấy mã nguồn dự án

```bat
cd %USERPROFILE%
# (Nếu đã có mã trong thư mục meeting-notes-summarizer thì bỏ qua bước clone)
```

Cấu trúc dự án:
```
meeting-notes-summarizer/
  backend/
  frontend/
  docs/
```

---

## 4) Cấu hình Backend (.env)

### 4.1 Tạo file .env tự động (khuyến nghị)

```bat
cd meeting-notes-summarizer\backend
python create_env.py
```
- Script sẽ hỏi:
  - AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT (lấy từ Azure Portal → OpenAI Resource → Keys and Endpoint)
  - AZURE_OPENAI_DEPLOYMENT_NAME (ví dụ: gpt-4, gpt-4o, gpt-4o-mini — phải đúng deployment đã tạo trong Azure)
  - DATABASE_URL, ví dụ:
    ```
    postgresql://postgres:<yourpassword>@localhost:5432/meeting_notes_summarizer
    ```
  - FRONTEND_URL (mặc định http://localhost:5173)

### 4.2 Tạo file .env thủ công (tuỳ chọn)
- Tạo file `meeting-notes-summarizer\backend\.env` với nội dung mẫu:
  ```env
  AZURE_OPENAI_API_KEY=your-api-key
  AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
  AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
  AZURE_OPENAI_API_VERSION=2024-08-01-preview
  DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/meeting_notes_summarizer
  ENVIRONMENT=development
  DEBUG=true
  SECRET_KEY=dev-secret-key
  FRONTEND_URL=http://localhost:5173
  ```

Lưu ý: Nếu mật khẩu PostgreSQL chứa ký tự đặc biệt (!, @, #, ...), bạn cần URL-encode trong `DATABASE_URL` (ví dụ: `@` → `%40`).

---

## 5) Cài dependencies và khởi tạo DB

### 5.1 Cài đặt Python packages
```bat
cd meeting-notes-summarizer\backend
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5.2 Khởi tạo database tables
```bat
python setup_db.py
```
- Kết quả mong đợi:
  - Tạo các bảng và user demo (id=1)

---

## 6) Chạy Backend

```bat
cd meeting-notes-summarizer\backend
.venv\Scripts\activate
python -m uvicorn app.main:app --reload --port 8000
```
- Mở: http://localhost:8000/docs để xem API

---

## 7) Chạy Frontend

```bat
cd meeting-notes-summarizer\frontend
npm install
npm run dev
```
- Mở: http://localhost:5173

Nếu Vite dùng port khác (ví dụ 5174), cập nhật `FRONTEND_URL` trong `backend/.env` và restart backend.

---

## 8) Test nhanh

- Dùng UI tab "Paste Text" → dán transcript mẫu trong `docs/SAMPLE_TRANSCRIPT.md` → Process
- Màn hình phải (Right panel): nếu chưa chọn meeting nào sẽ là danh sách meetings đã xử lý
- Chọn 1 meeting để xem chi tiết; có nút Back để quay lại danh sách
- Action Items hiển thị dạng card grid (3 card/hàng), có thể chỉnh sửa và lưu (PUT /api/meetings/{id})

---

## 9) Troubleshooting (Windows)

- Lỗi CORS: đảm bảo `FRONTEND_URL` đúng port (5173/5174), restart backend.
- Lỗi DB: kiểm tra service PostgreSQL đang chạy, `DATABASE_URL` đúng, database `meeting_notes_summarizer` tồn tại.
- Lỗi Azure OpenAI: kiểm tra API key/endpoint/deployment; endpoint phải có `/` ở cuối.
- Port bận: tắt tiến trình chiếm port hoặc đổi port trong lệnh uvicorn / vite.

---

## 10) Nâng cao

- Có thể dùng WSL để mô phỏng Linux; khi đó làm theo hướng dẫn Linux.
- Sản xuất: triển khai backend lên dịch vụ cloud (App Service/EC2…), frontend lên CDN (Vercel/Netlify…), DB dùng managed PostgreSQL.

