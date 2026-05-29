# 옷 쇼핑몰 — 데이터베이스 과제

## 프로젝트 구조

```
shop/
├── backend/
│   ├── main.py          # FastAPI 라우터 (API 전체)
│   ├── database.py      # PostgreSQL 연결 + 트랜잭션 관리
│   ├── auth.py          # 비밀번호 해싱, JWT 토큰
│   ├── requirements.txt
│   └── .env             # DB 접속 정보 (git에 올리면 안 됨)
├── sql/
│   └── schema.sql       # 테이블 정의 + 샘플 데이터
└── frontend/
    └── index.html       # 프론트엔드 (다음 단계)
```

---

## 1단계: PostgreSQL 데이터베이스 생성

터미널에서:

```bash
psql -U postgres
```

psql 접속 후:

```sql
CREATE DATABASE shopdb;
\q
```

그 다음 스키마 적용:

```bash
psql -U postgres -d shopdb -f sql/schema.sql
```

---

## 2단계: 백엔드 실행

```bash
cd backend

# 가상환경 만들기
python -m venv venv
source venv/bin/activate        # Mac/Linux
# 또는
venv\Scripts\activate           # Windows

# 패키지 설치
pip install -r requirements.txt

# .env 파일에 DB 비밀번호 입력 후 실행
uvicorn main:app --reload
```

서버 실행되면 → http://localhost:8000/docs 에서 API 테스트 가능 (Swagger UI 자동 생성)

---

## 데이터베이스 핵심 개념 정리

### 릴레이션 (Relation)
| 테이블 | 역할 |
|--------|------|
| users | 회원 정보 |
| products | 상품 정보 |
| cart | 장바구니 (users ↔ products 중간 테이블) |
| orders | 주문 헤더 |
| order_items | 주문 상세 (orders ↔ products 중간 테이블) |

### 주요 쿼리
- `SELECT ... JOIN` : 장바구니/주문 조회 시 여러 테이블 조인
- `INSERT ... ON CONFLICT` : 장바구니 UPSERT
- `UPDATE ... WHERE` : 재고 차감

### 트랜잭션 (Transaction)
`POST /orders` 에서 사용:
1. 재고 차감 (`UPDATE products`)
2. 주문 생성 (`INSERT INTO orders`)
3. 주문 상세 저장 (`INSERT INTO order_items`)
4. 장바구니 비우기 (`DELETE FROM cart`)

→ 4개 쿼리가 **모두 성공해야 커밋**, 하나라도 실패하면 **전부 롤백**
