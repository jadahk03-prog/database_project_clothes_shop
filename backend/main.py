from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import psycopg2

from database import get_connection, get_cursor
from auth import hash_password, verify_password, create_token, decode_token

app = FastAPI(title="옷 쇼핑몰 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 헬퍼: 토큰에서 user_id 추출 ──────────────────────────
def get_user_id(authorization: str = None) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    try:
        return decode_token(authorization.split(" ")[1])
    except Exception:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")

# ── Pydantic 모델 ─────────────────────────────────────────
class RegisterBody(BaseModel):
    email: str
    password: str
    name: str

class LoginBody(BaseModel):
    email: str
    password: str

class CartBody(BaseModel):
    product_id: int
    quantity: int = 1

class OrderBody(BaseModel):
    # 장바구니 전체를 주문으로 변환
    pass

# ═══════════════════════════════════════════════════════════
# 1. 회원 API
# ═══════════════════════════════════════════════════════════

@app.post("/api/register")
def register(body: RegisterBody):
    """회원가입 — INSERT"""
    conn = get_connection()
    cur = get_cursor(conn)
    try:
        cur.execute("SELECT id FROM users WHERE email = %s", (body.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다")
        hashed = hash_password(body.password)
        cur.execute(
            "INSERT INTO users (email, password, name) VALUES (%s, %s, %s) RETURNING id",
            (body.email, hashed, body.name)
        )
        user_id = cur.fetchone()["id"]
        conn.commit()
        return {"message": "회원가입 완료", "token": create_token(user_id)}
    finally:
        conn.close()

@app.post("/api/login")
def login(body: LoginBody):
    """로그인 — SELECT + 비밀번호 검증"""
    conn = get_connection()
    cur = get_cursor(conn)
    try:
        cur.execute("SELECT * FROM users WHERE email = %s", (body.email,))
        user = cur.fetchone()
        if not user or not verify_password(body.password, user["password"]):
            raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 틀렸습니다")
        return {"token": create_token(user["id"]), "name": user["name"]}
    finally:
        conn.close()

# ═══════════════════════════════════════════════════════════
# 2. 상품 API
# ═══════════════════════════════════════════════════════════

@app.get("/api/products")
def list_products(category: Optional[str] = None, search: Optional[str] = None):
    """상품 목록 — SELECT + 필터링"""
    conn = get_connection()
    cur = get_cursor(conn)
    try:
        sql = "SELECT * FROM products WHERE 1=1"
        params = []
        if category:
            sql += " AND category = %s"
            params.append(category)
        if search:
            sql += " AND name ILIKE %s"
            params.append(f"%{search}%")
        sql += " ORDER BY created_at DESC"
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.close()

@app.get("/api/products/{product_id}")
def get_product(product_id: int):
    """상품 상세"""
    conn = get_connection()
    cur = get_cursor(conn)
    try:
        cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
        product = cur.fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다")
        return product
    finally:
        conn.close()

# ═══════════════════════════════════════════════════════════
# 3. 장바구니 API
# ═══════════════════════════════════════════════════════════

@app.get("/api/cart")
def get_cart(authorization: Optional[str] = Header(None)):
    """장바구니 조회 — JOIN 쿼리"""
    user_id = get_user_id(authorization)
    conn = get_connection()
    cur = get_cursor(conn)
    try:
        cur.execute("""
            SELECT c.id, c.quantity, p.id as product_id,
                   p.name, p.price, p.image_url,
                   (c.quantity * p.price) as subtotal
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = %s
        """, (user_id,))
        items = cur.fetchall()
        total = sum(item["subtotal"] for item in items)
        return {"items": items, "total": total}
    finally:
        conn.close()

@app.post("/api/cart")
def add_to_cart(body: CartBody, authorization: Optional[str] = Header(None)):
    """장바구니 담기 — INSERT ON CONFLICT (UPSERT)"""
    user_id = get_user_id(authorization)
    conn = get_connection()
    cur = get_cursor(conn)
    try:
        cur.execute("""
            INSERT INTO cart (user_id, product_id, quantity)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, product_id)
            DO UPDATE SET quantity = cart.quantity + EXCLUDED.quantity
        """, (user_id, body.product_id, body.quantity))
        conn.commit()
        return {"message": "장바구니에 담겼습니다"}
    finally:
        conn.close()

@app.delete("/api/cart/{product_id}")
def remove_from_cart(product_id: int, authorization: Optional[str] = Header(None)):
    """장바구니 삭제"""
    user_id = get_user_id(authorization)
    conn = get_connection()
    cur = get_cursor(conn)
    try:
        cur.execute("DELETE FROM cart WHERE user_id = %s AND product_id = %s", (user_id, product_id))
        conn.commit()
        return {"message": "삭제되었습니다"}
    finally:
        conn.close()

# ═══════════════════════════════════════════════════════════
# 4. 주문 API  ← 트랜잭션 핵심 예시
# ═══════════════════════════════════════════════════════════

@app.post("/api/orders")
def create_order(authorization: Optional[str] = Header(None)):
    """
    주문 생성 — 트랜잭션(Transaction) 핵심!
    
    아래 3가지가 모두 성공해야 커밋, 하나라도 실패하면 롤백:
      1) 재고 확인 및 차감 (UPDATE products)
      2) 주문 레코드 생성 (INSERT orders)
      3) 주문 상세 생성  (INSERT order_items)
      4) 장바구니 비우기 (DELETE cart)
    """
    user_id = get_user_id(authorization)
    conn = get_connection()
    cur = get_cursor(conn)
    try:
        # 트랜잭션 시작 (psycopg2는 기본적으로 autocommit=False)
        
        # 장바구니 조회
        cur.execute("""
            SELECT c.quantity, p.id as product_id, p.price, p.stock, p.name
            FROM cart c JOIN products p ON c.product_id = p.id
            WHERE c.user_id = %s
        """, (user_id,))
        cart_items = cur.fetchall()

        if not cart_items:
            raise HTTPException(status_code=400, detail="장바구니가 비어있습니다")

        # 재고 확인
        for item in cart_items:
            if item["stock"] < item["quantity"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"'{item['name']}' 재고가 부족합니다 (남은 재고: {item['stock']}개)"
                )

        total_price = sum(item["price"] * item["quantity"] for item in cart_items)

        # ① 주문 생성
        cur.execute(
            "INSERT INTO orders (user_id, total_price, status) VALUES (%s, %s, 'paid') RETURNING id",
            (user_id, total_price)
        )
        order_id = cur.fetchone()["id"]

        for item in cart_items:
            # ② 주문 상세 저장
            cur.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)",
                (order_id, item["product_id"], item["quantity"], item["price"])
            )
            # ③ 재고 차감
            cur.execute(
                "UPDATE products SET stock = stock - %s WHERE id = %s",
                (item["quantity"], item["product_id"])
            )

        # ④ 장바구니 비우기
        cur.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))

        conn.commit()  # 모두 성공 → 커밋
        return {"message": "주문이 완료되었습니다", "order_id": order_id, "total_price": total_price}

    except HTTPException:
        conn.rollback()  # 실패 → 롤백
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/orders")
def get_orders(authorization: Optional[str] = Header(None)):
    """주문 내역 조회 — JOIN 쿼리"""
    user_id = get_user_id(authorization)
    conn = get_connection()
    cur = get_cursor(conn)
    try:
        cur.execute("""
            SELECT o.id, o.total_price, o.status, o.created_at,
                   json_agg(json_build_object(
                       'product_name', p.name,
                       'quantity', oi.quantity,
                       'price', oi.price
                   )) as items
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            WHERE o.user_id = %s
            GROUP BY o.id
            ORDER BY o.created_at DESC
        """, (user_id,))
        return cur.fetchall()
    finally:
        conn.close()

@app.get("/")
def root():
    return {"message": "옷 쇼핑몰 API 서버 실행 중 🛍️"}
