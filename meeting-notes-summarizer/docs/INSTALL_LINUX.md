# Hướng dẫn cài đặt và chạy ứng dụng trên Linux (Ubuntu/Debian/WSL)

Tài liệu này hướng dẫn thiết lập môi trường và chạy Meeting Notes Summarizer trên Linux (Ubuntu/Debian) hoặc WSL (Windows Subsystem for Linux). Bao gồm: PostgreSQL, Python, Node.js; cấu hình Azure OpenAI; khởi tạo DB; chạy backend và frontend.

---

## 1) Yêu cầu hệ thống
- Ubuntu/Debian hoặc WSL Ubuntu 22.04+/24.04+
- Python 3.12+
- Node.js LTS
- PostgreSQL 14+ (hoặc 16)

---

## 2) Cài đặt phần mềm cần thiết

### 2.1 PostgreSQL
```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
```
Start service (trên WSL dùng service thay vì systemctl):
```bash
sudo service postgresql start
sudo service postgresql status
```
Tạo database `meeting_notes_summarizer`:
```bash
sudo -u postgres psql -c "CREATE DATABASE meeting_notes_summarizer;"
```
Đặt/đổi mật khẩu user `postgres` (tuỳ chọn):
```bash
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'yourpassword';"
```

### 2.2 Python 3.12+
- Ubuntu 24.04 thường đã có Python 3.12. Kiểm tra:
```bash
python3 --version
```
Khuyến nghị dùng venv:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

(WSL + pyenv-virtualenv) — tuỳ chọn nâng cao
```bash
# Nếu dùng pyenv
pyenv install 3.12.0
pyenv virtualenv 3.12.0 mns-312
pyenv local mns-312
```

### 2.3 Node.js LTS
Dùng nvm (khuyến nghị):
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm install --lts
nvm use --lts
```

---

## 3) Lấy mã nguồn dự án
```bash
cd ~
# Nếu project đã có sẵn, bỏ qua bước clone
# cd meeting-notes-summarizer
```
Cấu trúc
```
meeting-notes-summarizer/
  backend/
  frontend/
  docs/
```

---

## 4) Cấu hình Backend (.env)

### 4.1 Tạo file .env tự động (khuyến nghị)
```bash
cd meeting-notes-summarizer/backend
python create_env.py
```
Nhập:
- AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT (Azure Portal → OpenAI Resource → Keys and Endpoint)
- AZURE_OPENAI_DEPLOYMENT_NAME (ví dụ gpt-4, gpt-4o, gpt-4o-mini — đúng tên deployment bạn đã tạo)
- DATABASE_URL, ví dụ:
  ```
  postgresql://postgres:<password>@localhost:5432/meeting_notes_summarizer
  ```
- FRONTEND_URL mặc định http://localhost:5173

Lưu ý: Nếu mật khẩu Postgres có ký tự đặc biệt (!, @, #, ...), hãy URL-encode trong `DATABASE_URL`.

### 4.2 Tạo .env thủ công (tuỳ chọn)
Tạo file `backend/.env`:
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

---

## 5) Cài dependencies & khởi tạo DB

### 5.1 Cài đặt Python packages
```bash
cd meeting-notes-summarizer/backend
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5.2 Khởi tạo database tables
```bash
python setup_db.py
```
Kỳ vọng: tạo bảng + user demo (id=1).

---

## 6) Chạy Backend
```bash
cd meeting-notes-summarizer/backend
source .venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```
Mở http://localhost:8000/docs để xem API.

---

## 7) Chạy Frontend
```bash
cd meeting-notes-summarizer/frontend
npm install
npm run dev
```
Mặc định Vite ở http://localhost:5173. Nếu đổi port (VD 5174), cập nhật `FRONTEND_URL` trong `backend/.env` và restart backend.

---

## 8) Test nhanh
- UI tab "Paste Text" → dán transcript mẫu `docs/SAMPLE_TRANSCRIPT.md` → Process
- Panel phải (Right panel):
  - Khi chưa chọn meeting → danh sách meetings (GET /api/meetings)
  - Click 1 meeting → xem chi tiết (GET /api/meetings/{id})
  - Nút Back trong chi tiết → quay lại danh sách
- Action Items hiển thị card grid (3 card/hàng), cho phép chỉnh và lưu (PUT /api/meetings/{id}).

---

## 9) Troubleshooting (Linux/WSL)
- PostgreSQL không chạy:
  ```bash
  sudo service postgresql start
  sudo service postgresql status
  ```
- Kết nối DB lỗi: kiểm tra `DATABASE_URL`, DB đã tạo chưa, mật khẩu đã URL-encode.
- Lỗi Azure OpenAI: xác minh key/endpoint/deployment name; endpoint phải có dấu `/` ở cuối.
- CORS: FRONTEND_URL phải trùng port Vite; sửa .env và restart backend.
- Port bận: dừng tiến trình đang chiếm port hoặc đổi port.

---

## 10) Gợi ý triển khai sản xuất
- Backend: triển khai lên cloud (AWS/Azure/GCP)
- Frontend: CDN (Vercel/Netlify)
- DB: Managed PostgreSQL
- Secrets: lưu trong Secret Manager/Key Vault

