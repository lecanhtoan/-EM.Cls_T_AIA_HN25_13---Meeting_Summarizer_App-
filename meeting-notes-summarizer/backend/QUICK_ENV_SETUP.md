# Quick Environment Setup

## Option 1: Interactive Script (Recommended) ⭐

Chạy script Python tương tác để tạo `.env`:

```bash
cd backend
python create_env.py
```

Script sẽ hỏi bạn từng thông tin:
1. Azure OpenAI API Key
2. Azure OpenAI Endpoint
3. Azure OpenAI Deployment Name
4. PostgreSQL credentials
5. Application settings

Sau đó tự động tạo file `.env`.

### Ví dụ Chạy Script:

```
$ python create_env.py

======================================================================
Meeting Notes Summarizer - Environment Setup
======================================================================

----------------------------------------------------------------------
AZURE OPENAI CONFIGURATION
----------------------------------------------------------------------
Get these from Azure Portal: https://portal.azure.com/

Azure OpenAI API Key: sk-proj-abc123def456
Azure OpenAI Endpoint (e.g., https://resource.openai.azure.com/) [https://your-resource.openai.azure.com/]: https://my-resource.openai.azure.com/
Azure OpenAI Deployment Name (e.g., gpt-4) [gpt-4]: gpt-4
Azure OpenAI API Version [2024-08-01-preview]: 

----------------------------------------------------------------------
POSTGRESQL CONFIGURATION
----------------------------------------------------------------------
Format: postgresql://username:password@host:port/database

PostgreSQL Username [postgres]: postgres
PostgreSQL Password [password]: mypassword
PostgreSQL Host [localhost]: localhost
PostgreSQL Port [5432]: 5432
PostgreSQL Database Name [meeting_notes_summarizer]: meeting_notes_summarizer

----------------------------------------------------------------------
APPLICATION SETTINGS
----------------------------------------------------------------------

Environment (development/production) [development]: development
Debug Mode (true/false) [true]: true
Secret Key [dev-secret-key-change-in-production]: 
Frontend URL [http://localhost:5173]: 

======================================================================
✅ .env file created successfully!
======================================================================

File location: /path/to/backend/.env

Configuration summary:
  Azure OpenAI API Key: sk-proj-abc...
  Azure OpenAI Endpoint: https://my-resource.openai.azure.com/
  Azure OpenAI Deployment: gpt-4
  PostgreSQL Database: localhost:5432/meeting_notes_summarizer
  Environment: development
  Frontend URL: http://localhost:5173

----------------------------------------------------------------------
NEXT STEPS
----------------------------------------------------------------------

1. Initialize database:
   python setup_db.py

2. Start backend server:
   python -m uvicorn app.main:app --reload

3. In another terminal, start frontend:
   cd ../frontend
   npm run dev

4. Open application:
   Frontend: http://localhost:5173
   API Docs: http://localhost:8000/docs
```

---

## Option 2: Manual Setup

Nếu không muốn dùng script, tạo file `.env` thủ công:

### Step 1: Tạo File

Tại thư mục `backend/`, tạo file `.env` (không có phần mở rộng)

### Step 2: Copy Nội Dung

```env
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# PostgreSQL Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/meeting_notes_summarizer

# Application Settings
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=dev-secret-key-change-in-production

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:5173
```

### Step 3: Điền Thông Tin

Thay thế các placeholder bằng giá trị thực của bạn.

Xem `ENV_SETUP_GUIDE.md` để biết chi tiết.

---

## Lấy Azure OpenAI Credentials

### 1. API Key

- Đi tới: https://portal.azure.com/
- Tìm Azure OpenAI resource
- Vào "Keys and Endpoint"
- Copy "Key 1" hoặc "Key 2"

### 2. Endpoint

- Vẫn ở "Keys and Endpoint"
- Copy "Endpoint" (đảm bảo có `/` ở cuối)

### 3. Deployment Name

- Vào "Model deployments"
- Tìm GPT-4 deployment
- Copy tên deployment

---

## Lấy PostgreSQL Credentials

### Nếu PostgreSQL Chạy Local

```bash
# Kiểm tra PostgreSQL đang chạy
psql -U postgres -c "SELECT 1;"

# Nếu chưa tạo database
createdb meeting_notes_summarizer

# Kiểm tra database tồn tại
psql -U postgres -l | grep meeting_notes_summarizer
```

### Thông Tin Mặc Định

- Username: `postgres`
- Password: Mật khẩu bạn đặt khi cài PostgreSQL
- Host: `localhost`
- Port: `5432`
- Database: `meeting_notes_summarizer`

---

## Xác Minh Setup

Sau khi tạo `.env`, kiểm tra:

```bash
# Kiểm tra file tồn tại
ls -la .env

# Kiểm tra nội dung (không hiển thị giá trị nhạy cảm)
cat .env | grep -v "KEY\|PASSWORD"

# Kiểm tra cấu hình được load
python -c "from app.config import settings; print('✅ Config loaded successfully')"
```

---

## Troubleshooting

### Lỗi: "No such file or directory: '.env'"

```bash
# Kiểm tra file tồn tại
ls -la backend/.env

# Nếu không tồn tại, chạy script lại
python create_env.py
```

### Lỗi: "could not connect to server"

```bash
# Kiểm tra PostgreSQL chạy
psql -U postgres -c "SELECT 1;"

# Kiểm tra database tồn tại
createdb meeting_notes_summarizer

# Kiểm tra DATABASE_URL trong .env
cat .env | grep DATABASE_URL
```

### Lỗi: "Invalid API key"

```bash
# Kiểm tra API key
cat .env | grep AZURE_OPENAI_API_KEY

# Kiểm tra endpoint
cat .env | grep AZURE_OPENAI_ENDPOINT
```

---

## Tiếp Theo

Sau khi setup `.env`:

```bash
# 1. Initialize database
python setup_db.py

# 2. Run backend
python -m uvicorn app.main:app --reload

# 3. In another terminal, run frontend
cd ../frontend
npm run dev

# 4. Open http://localhost:5173
```

---

**Cần giúp?** Xem `ENV_SETUP_GUIDE.md` để biết chi tiết.


