-- =============================================
-- 옷 쇼핑몰 데이터베이스 스키마
-- =============================================

-- 기존 테이블 삭제 (개발 초기화용)
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS cart CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ① 회원 테이블
CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    email       VARCHAR(255) UNIQUE NOT NULL,
    password    VARCHAR(255) NOT NULL,         -- bcrypt 해시
    name        VARCHAR(100) NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ② 상품 테이블
CREATE TABLE products (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    price       INTEGER NOT NULL CHECK (price >= 0),
    stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    category    VARCHAR(100),                  -- 예: '상의', '하의', '아우터'
    image_url   VARCHAR(500),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ③ 주문 테이블
CREATE TABLE orders (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    total_price INTEGER NOT NULL,
    status      VARCHAR(50) DEFAULT 'pending', -- pending / paid / shipped / delivered
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ④ 주문 상세 테이블 (주문-상품 다대다 연결)
CREATE TABLE order_items (
    id          SERIAL PRIMARY KEY,
    order_id    INTEGER NOT NULL REFERENCES orders(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    price       INTEGER NOT NULL              -- 주문 당시 가격 스냅샷
);

-- ⑤ 장바구니 테이블
CREATE TABLE cart (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    UNIQUE (user_id, product_id)              -- 같은 상품은 수량만 변경
);

-- =============================================
-- 샘플 데이터
-- =============================================
INSERT INTO products (name, description, price, stock, category, image_url) VALUES
('오버핏 코튼 티셔츠', '부드러운 순면 소재의 오버핏 반팔티', 29000, 50, '상의', 'https://picsum.photos/seed/tshirt/400/500'),
('슬림 데님 팬츠', '클래식한 슬림핏 청바지', 59000, 30, '하의', 'https://picsum.photos/seed/jeans/400/500'),
('울 블렌드 코트', '따뜻한 울 혼방 롱 코트', 189000, 15, '아우터', 'https://picsum.photos/seed/coat/400/500'),
('린넨 버튼업 셔츠', '시원한 린넨 소재 반팔 셔츠', 49000, 40, '상의', 'https://picsum.photos/seed/shirt/400/500'),
('와이드 슬랙스', '편안한 와이드핏 슬랙스', 69000, 25, '하의', 'https://picsum.photos/seed/slacks/400/500'),
('후드 집업', '기본 후드 집업 자켓', 79000, 35, '아우터', 'https://picsum.photos/seed/hoodie/400/500');
