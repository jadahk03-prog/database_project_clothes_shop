# 옷 쇼핑몰 — DB 과제 프로젝트

## 기술 스택
- **백엔드**: FastAPI (Python)
- **DB**: PostgreSQL
- **프론트엔드**: HTML/CSS/JS (바닐라)

## 시작하기

### 1. DB 설정
```bash
# PostgreSQL에서 DB 생성
psql -U postgres -c "CREATE DATABASE shop_db;"

# 스키마 + 샘플 데이터 적용
psql -U postgres -d shop_db -f sql/schema.sql
```

### 2. 백엔드 실행
```bash
cd backend

# 패키지 설치 (최초 1회)
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일에서 DB_PASSWORD 수정

# 서버 실행
uvicorn main:app --reload
```

### 3. 프론트엔드 열기
```bash
# frontend/index.html 을 브라우저에서 직접 열거나
# 간단한 서버로 열기:
cd frontend
python -m http.server 3000
# → http://localhost:3000 접속
```

## DB 구조 (Relation)

| 테이블 | 설명 |
|--------|------|
| users | 회원 정보 |
| products | 상품 (재고 포함) |
| orders | 주문 헤더 |
| order_items | 주문 상세 (orders ↔ products 다대다) |
| cart | 장바구니 |

## 트랜잭션 포인트

`POST /api/orders` — 주문 생성 시:
1. 재고 확인
2. orders INSERT
3. order_items INSERT
4. products.stock 차감 (UPDATE)
5. cart DELETE

→ 하나라도 실패하면 `ROLLBACK`, 전부 성공해야 `COMMIT`

## API 목록

| Method | Path | 설명 |
|--------|------|------|
| POST | /api/register | 회원가입 |
| POST | /api/login | 로그인 |
| GET | /api/products | 상품 목록 (카테고리/검색 필터) |
| GET | /api/products/{id} | 상품 상세 |
| GET | /api/cart | 장바구니 조회 |
| POST | /api/cart | 장바구니 담기 |
| DELETE | /api/cart/{product_id} | 장바구니 삭제 |
| POST | /api/orders | **주문 생성 (트랜잭션)** |
| GET | /api/orders | 주문 내역 |
