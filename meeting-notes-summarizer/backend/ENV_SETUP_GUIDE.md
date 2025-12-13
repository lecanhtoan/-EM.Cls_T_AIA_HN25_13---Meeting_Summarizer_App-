# Backend Environment Setup Guide

## Tạo File `.env`

File `.env` được ignore bởi Git vì chứa thông tin nhạy cảm. Bạn cần tạo nó thủ công.

### Bước 1: Tạo File `.env`

Tại thư mục `backend/`, tạo file mới tên là `.env` (không có phần mở rộng).

### Bước 2: Copy Nội Dung Dưới Đây

Sao chép toàn bộ nội dung bên dưới vào file `.env`:

```env
# Azure OpenAI Configuration
# Get these from Azure Portal: https://portal.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# PineCone configuration + embedding model
PINECONE_API_KEY=<YOUR_PINECONE_API_KEY>
PINECONE_INDEX_NAME=meeting-summaries
PINECONE_NAMESPACE=default
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

AZURE_OPENAI_EMBEDDING_API_KEY=your-api-key-here
AZURE_OPENAI_EMBEDDING_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=text-embedding-3-small
AZURE_OPENAI_EMBEDDING_API_VERSION=2024-08-01-preview

# PostgreSQL Configuration
# Format: postgresql://username:password@host:port/database
# Example: postgresql://postgres:password@localhost:5432/meeting_notes_summarizer
DATABASE_URL=postgresql://postgres:password@localhost:5432/meeting_notes_summarizer

# Application Settings
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=dev-secret-key-change-in-production

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:5173
```

### Bước 3: Điền Thông Tin

Thay thế các placeholder bằng thông tin thực của bạn:

#### 3.1 Azure OpenAI Credentials

**AZURE_OPENAI_API_KEY**
- Đi tới: https://portal.azure.com/
- Tìm Azure OpenAI resource của bạn
- Vào "Keys and Endpoint"
- Copy "Key 1" hoặc "Key 2"
- Dán vào: `AZURE_OPENAI_API_KEY=your-actual-key-here`

**AZURE_OPENAI_ENDPOINT**
- Vẫn ở "Keys and Endpoint"
- Copy "Endpoint"
- Dán vào: `AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/`
- Đảm bảo có dấu `/` ở cuối

**AZURE_OPENAI_DEPLOYMENT_NAME**
- Vào "Model deployments" trong Azure OpenAI resource
- Tìm deployment GPT-4
- Copy tên deployment (thường là `gpt-4` hoặc tên custom)
- Dán vào: `AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4`

**AZURE_OPENAI_API_VERSION**
- Giữ nguyên: `2024-08-01-preview`
- Hoặc cập nhật nếu có version mới

#### 3.2 PostgreSQL Connection

**DATABASE_URL**
- Nếu PostgreSQL chạy local mặc định:
  ```
  DATABASE_URL=postgresql://postgres:password@localhost:5432/meeting_notes_summarizer
  ```
  
- Thay `password` bằng mật khẩu postgres của bạn
- Nếu user khác, thay `postgres` bằng username
- Nếu port khác, thay `5432` bằng port thực

**Ví dụ:**
```
DATABASE_URL=postgresql://postgres:mypassword123@localhost:5432/meeting_notes_summarizer
```

#### 3.3 Application Settings

**ENVIRONMENT**
- Giữ nguyên `development` cho local
- Đổi thành `production` khi deploy

**DEBUG**
- Giữ nguyên `true` cho local
- Đổi thành `false` khi deploy

**SECRET_KEY**
- Giữ nguyên `dev-secret-key-change-in-production` cho local
- Tạo key mạnh khi deploy (dùng: `python -c "import secrets; print(secrets.token_urlsafe(32))"`)

**FRONTEND_URL**
- Giữ nguyên `http://localhost:5173` cho local
- Đổi thành URL frontend thực khi deploy

### Bước 4: Lưu File

Lưu file `.env` và đảm bảo nó ở đúng vị trí:
```
meeting-notes-summarizer/
└── backend/
    └── .env  ← File này
```

### Bước 5: Xác Minh

Kiểm tra file được tạo đúng:
```bash
cd backend
cat .env  # macOS/Linux
type .env # Windows
```

Bạn sẽ thấy các biến môi trường đã điền.

## Kiểm Tra Kết Nối

Sau khi tạo `.env`, kiểm tra kết nối:

### 1. Kiểm Tra PostgreSQL
```bash
cd backend
python -c "from app.config import settings; print(f'DB: {settings.database_url}')"
```

### 2. Kiểm Tra Azure OpenAI
```bash
cd backend
python -c "from app.config import settings; print(f'API Key: {settings.azure_openai_api_key[:10]}...')"
```

## Troubleshooting

### Lỗi: "No such file or directory: '.env'"
- Đảm bảo file `.env` được tạo ở đúng vị trí: `backend/.env`
- Kiểm tra tên file không có phần mở rộng (không phải `.env.txt`)

### Lỗi: "AZURE_OPENAI_API_KEY not found"
- Kiểm tra file `.env` có chứa `AZURE_OPENAI_API_KEY=...`
- Đảm bảo không có khoảng trắng thừa: `AZURE_OPENAI_API_KEY = ...` (sai)
- Phải là: `AZURE_OPENAI_API_KEY=...` (đúng)

### Lỗi: "could not connect to server"
- Kiểm tra PostgreSQL đang chạy: `psql -U postgres -c "SELECT 1;"`
- Kiểm tra DATABASE_URL đúng: `postgresql://user:password@host:port/database`
- Kiểm tra database tồn tại: `createdb meeting_notes_summarizer`

### Lỗi: "Invalid API key"
- Kiểm tra API key đúng từ Azure Portal
- Kiểm tra endpoint URL có dấu `/` ở cuối
- Kiểm tra deployment GPT-4 tồn tại

## Ví Dụ Hoàn Chỉnh

File `.env` hoàn chỉnh sau khi điền:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=sk-proj-abc123def456ghi789jkl
AZURE_OPENAI_ENDPOINT=https://my-openai-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# PostgreSQL Configuration
DATABASE_URL=postgresql://postgres:mypassword@localhost:5432/meeting_notes_summarizer

# Application Settings
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=dev-secret-key-change-in-production

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:5173
```

## Bảo Mật

⚠️ **QUAN TRỌNG**: 
- Không commit file `.env` lên Git
- File `.env` đã được thêm vào `.gitignore`
- Không chia sẻ file `.env` với ai
- Không đăng `.env` lên GitHub/công khai

## Tiếp Theo

Sau khi tạo `.env`:

1. Chạy database setup:
   ```bash
   python setup_db.py
   ```

2. Chạy backend:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

3. Kiểm tra API docs:
   ```
   http://localhost:8000/docs
   ```

---

**Cần giúp?** Xem `SETUP_INSTRUCTIONS.md` hoặc `RUN_INSTRUCTIONS.md`


