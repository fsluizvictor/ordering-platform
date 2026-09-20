-- =============================================================================
-- Seed SQL — Fallback direto no PostgreSQL (bypassa a API e o Worker).
-- Use apenas quando não for possível rodar o seed via HTTP.
--
-- ATENÇÃO: Este script insere dados diretamente no banco, sem passar pelas
-- regras de negócio da aplicação. Use o seed.py sempre que possível.
--
-- Como executar:
--   docker compose exec postgres psql -U ordering -f /dev/stdin < scripts/seed.sql
--
-- Ou, conectando ao container:
--   docker compose exec postgres psql -U ordering
--   \c customer_db   (depois copie e cole cada bloco)
-- =============================================================================


-- ---------------------------------------------------------------------------
-- customer_db
-- ---------------------------------------------------------------------------

\c customer_db

INSERT INTO customers (id, name, email, phone, created_at, updated_at) VALUES
  ('a1000000-0000-0000-0000-000000000001', 'Alice Souza',   'alice.souza@example.com',   '+55 11 91234-5678', NOW(), NOW()),
  ('a1000000-0000-0000-0000-000000000002', 'Bruno Lima',    'bruno.lima@example.com',    '+55 21 99876-5432', NOW(), NOW()),
  ('a1000000-0000-0000-0000-000000000003', 'Carla Mendes',  'carla.mendes@example.com',  '+55 31 98765-4321', NOW(), NOW()),
  ('a1000000-0000-0000-0000-000000000004', 'Daniel Costa',  'daniel.costa@example.com',  '+55 41 97654-3210', NOW(), NOW()),
  ('a1000000-0000-0000-0000-000000000005', 'Eva Rocha',     'eva.rocha@example.com',     '+55 51 96543-2109', NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

SELECT COUNT(*) AS total_customers FROM customers;


-- ---------------------------------------------------------------------------
-- product_db
-- ---------------------------------------------------------------------------

\c product_db

INSERT INTO products (id, name, description, price, stock, created_at, updated_at) VALUES
  ('b2000000-0000-0000-0000-000000000001', 'Notebook Pro 15',         'Laptop profissional com processador de última geração, 16GB RAM e SSD 512GB.', 4599.90, 25,  NOW(), NOW()),
  ('b2000000-0000-0000-0000-000000000002', 'Mouse Sem Fio Ergonômico', 'Mouse óptico sem fio com design ergonômico e autonomia de 12 meses.',          129.90, 150, NOW(), NOW()),
  ('b2000000-0000-0000-0000-000000000003', 'Teclado Mecânico RGB',     'Teclado mecânico com switches blue, retroiluminação RGB e layout ABNT2.',      349.90,  80, NOW(), NOW()),
  ('b2000000-0000-0000-0000-000000000004', 'Monitor Ultrawide 34"',    'Monitor curvo ultrawide 34 polegadas, resolução 3440x1440, 144Hz.',            2899.00,  12, NOW(), NOW()),
  ('b2000000-0000-0000-0000-000000000005', 'Headset Gamer 7.1',        'Headset com som surround 7.1 virtual, microfone removível e almofadas memory foam.', 299.90, 60, NOW(), NOW()),
  ('b2000000-0000-0000-0000-000000000006', 'SSD NVMe 1TB',             'SSD com interface NVMe PCIe 4.0, leitura até 7000 MB/s.',                      549.90,  45, NOW(), NOW()),
  ('b2000000-0000-0000-0000-000000000007', 'Webcam Full HD 1080p',     'Webcam com resolução 1080p, autofoco e microfone embutido com cancelamento de ruído.', 199.90, 90, NOW(), NOW()),
  ('b2000000-0000-0000-0000-000000000008', 'Hub USB-C 7 em 1',         'Concentrador USB-C com HDMI 4K, USB 3.0 x3, SD, microSD e carregamento PD 100W.', 179.90, 110, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

SELECT COUNT(*) AS total_products FROM products;


-- ---------------------------------------------------------------------------
-- order_db  (apenas se quiser simular pedidos já COMPLETED sem o Worker)
-- ---------------------------------------------------------------------------
-- ATENÇÃO: Os IDs de customer_id e product_id abaixo correspondem aos UUIDs
-- fixos inseridos acima. Ajuste se usar o seed via HTTP (IDs serão gerados
-- dinamicamente).

\c order_db

-- Pedido 1: Alice — Notebook + Mouse
INSERT INTO orders (id, external_id, customer_id, status, total_amount, created_at, updated_at) VALUES
  ('c3000000-0000-0000-0000-000000000001',
   'e4000000-0000-0000-0000-000000000001',
   'a1000000-0000-0000-0000-000000000001',
   'COMPLETED', 4859.70, NOW(), NOW())
ON CONFLICT (external_id) DO NOTHING;

INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) VALUES
  ('d5000000-0000-0000-0000-000000000001', 'c3000000-0000-0000-0000-000000000001', 'b2000000-0000-0000-0000-000000000001', 1, 4599.90),
  ('d5000000-0000-0000-0000-000000000002', 'c3000000-0000-0000-0000-000000000001', 'b2000000-0000-0000-0000-000000000002', 2,  129.90)
ON CONFLICT (id) DO NOTHING;

-- Pedido 2: Bruno — Teclado + Headset
INSERT INTO orders (id, external_id, customer_id, status, total_amount, created_at, updated_at) VALUES
  ('c3000000-0000-0000-0000-000000000002',
   'e4000000-0000-0000-0000-000000000002',
   'a1000000-0000-0000-0000-000000000002',
   'COMPLETED', 649.80, NOW(), NOW())
ON CONFLICT (external_id) DO NOTHING;

INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) VALUES
  ('d5000000-0000-0000-0000-000000000003', 'c3000000-0000-0000-0000-000000000002', 'b2000000-0000-0000-0000-000000000003', 1, 349.90),
  ('d5000000-0000-0000-0000-000000000004', 'c3000000-0000-0000-0000-000000000002', 'b2000000-0000-0000-0000-000000000005', 1, 299.90)
ON CONFLICT (id) DO NOTHING;

-- Pedido 3: Carla — Monitor
INSERT INTO orders (id, external_id, customer_id, status, total_amount, created_at, updated_at) VALUES
  ('c3000000-0000-0000-0000-000000000003',
   'e4000000-0000-0000-0000-000000000003',
   'a1000000-0000-0000-0000-000000000003',
   'COMPLETED', 2899.00, NOW(), NOW())
ON CONFLICT (external_id) DO NOTHING;

INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) VALUES
  ('d5000000-0000-0000-0000-000000000005', 'c3000000-0000-0000-0000-000000000003', 'b2000000-0000-0000-0000-000000000004', 1, 2899.00)
ON CONFLICT (id) DO NOTHING;

SELECT COUNT(*) AS total_orders FROM orders;
SELECT COUNT(*) AS total_order_items FROM order_items;
