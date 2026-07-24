# Spin-up steps (run from the repo root `C:\Users\abhis\Desktop\abhimart`)

**1. Start Postgres (pgvector) via Docker** — make sure Docker Desktop is running first:

```bash
docker compose -f infra/docker-compose.yml up -d
```

```bash
(backend) 
abhis@Tinku MINGW64 ~/Desktop/abhimart (main)
$ docker compose -f infra/docker-compose.yml up -d
[+] up 3/3
 ✔ Network infra_default       Created                                                 0.0s
 ✔ Container abhimart-postgres Started                                                 0.9s
 ✔ Container abhimart-jaeger   Started                                                 0.9s
```

**2. Install deps** (into the existing `backend/.venv`):

```bash
cd backend; uv sync
```

**3. Run migrations:**

```bash
uv run alembic upgrade head
```

```bash
(backend) 
abhis@Tinku MINGW64 ~/Desktop/abhimart/backend (main)
$ uv run alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

**4. Seed products/users/orders:**

```bash
uv run python -m app.seed
```

```bash
(backend) 
abhis@Tinku MINGW64 ~/Desktop/abhimart/backend (main)
$ uv run python -m app.seed
2026-07-24 22:46:52,846 INFO sqlalchemy.engine.Engine select pg_catalog.version()
2026-07-24 22:46:52,846 INFO sqlalchemy.engine.Engine [raw sql] ()
2026-07-24 22:46:52,850 INFO sqlalchemy.engine.Engine select current_schema()
2026-07-24 22:46:52,850 INFO sqlalchemy.engine.Engine [raw sql] ()
2026-07-24 22:46:52,853 INFO sqlalchemy.engine.Engine show standard_conforming_strings
2026-07-24 22:46:52,853 INFO sqlalchemy.engine.Engine [raw sql] ()
2026-07-24 22:46:52,855 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2026-07-24 22:46:52,856 INFO sqlalchemy.engine.Engine DELETE FROM orders
2026-07-24 22:46:52,856 INFO sqlalchemy.engine.Engine [generated in 0.00017s] ()
2026-07-24 22:46:52,867 INFO sqlalchemy.engine.Engine DELETE FROM users
2026-07-24 22:46:52,867 INFO sqlalchemy.engine.Engine [generated in 0.00022s] ()
2026-07-24 22:46:52,870 INFO sqlalchemy.engine.Engine DELETE FROM products
2026-07-24 22:46:52,870 INFO sqlalchemy.engine.Engine [generated in 0.00020s] ()
2026-07-24 22:46:52 [info     ] Cleared existing data         
2026-07-24 22:46:52,882 INFO sqlalchemy.engine.Engine INSERT INTO products (id, name, description, price, category, sku, stock_quantity, is_active) VALUES ($1::UUID, $2::VARCHAR, $3::VARCHAR, $4::NUMERIC(10, 2), $5::VARCHAR, $6::VARCHAR, $7::INTEGER, $8::BOOLEAN), ($9::UUID, $10::VARCHAR, $11::VARCHAR,  ... 2729 characters truncated ... RCHAR, $191::INTEGER, $192::BOOLEAN) RETURNING products.created_at, products.updated_at, products.id
2026-07-24 22:46:52,883 INFO sqlalchemy.engine.Engine [generated in 0.00022s (insertmanyvalues) 1/1 (ordered)] (UUID('2bb4a545-cea5-4a84-9a47-12fbc0d507a7'), 'MacBook Pro 16-inch M3 Max', 'Apple M3 Max chip, 36GB unified memory, 1TB SSD, 16-inch Liquid Retina XDR display. Perfect for professional video editing and software development.', 2499.99, 'electronics', 'ELEC-MBP16-001', 25, True, UUID('0fa5e7a4-d47f-4ed2-9d95-530f043dc1c4'), 'iPhone 16 Pro Max', 'A18 Pro chip, 6.9-inch Super Retina XDR display, 48MP camera system, titanium design. 256GB storage.', 1199.99, 'electronics', 'ELEC-IP16PM-001', 100, True, UUID('9bfe95c0-e688-4288-aa98-4db95bbd6a03'), 'Sony WH-1000XM5 Headphones', 'Industry-leading noise cancellation, 30-hour battery life, crystal clear hands-free calling. Lightweight and comfortable.', 349.99, 'electronics', 'ELEC-SNYWH5-001', 75, True, UUID('96aa10f2-a372-4152-845d-ec156c6509ec'), 'Samsung Galaxy Tab S9 Ultra', '14.6-inch Dynamic AMOLED 2X display, Snapdragon 8 Gen 2, 12GB RAM, S Pen included. Great for digital art.', 1199.99, 'electronics', 'ELEC-SGTS9U-001', 40, True, UUID('6b3cbcf7-db5e-4079-b9b2-184a1ec39d7e'), 'Logitech MX Master 3S Mouse', 'Ergonomic wireless mouse with MagSpeed scroll, 8K DPI sensor, USB-C charging. Works on any surface including glass.', 99.99, 'electronics', 'ELEC-LMXM3S-001', 200, True, UUID('9e1374a2-1c46-4ce2-8f69-bf2850f29e88'), 'Dell UltraSharp 27 4K Monitor', '27-inch 4K UHD IPS display, USB-C hub with 90W charging, 98% DCI-P3 color coverage. Factory calibrated.', 619.99, 'electronics', 'ELEC-DU274K-001', 35, True, UUID('b72081af-ad28-4bcc-a69c-b58894b47093'), 'Instant Pot Pro Plus 6-Quart' ... 92 parameters truncated ... 150, True, UUID('37f169b3-a228-40aa-bd08-9520a1dfff08'), 'Designing Data-Intensive Applications', 'By Martin Kleppmann. The must-read guide to distributed systems, databases, and data pipelines. Essential for backend engineers.', 44.99, 'books', 'BOOK-DDIA-001', 200, True, UUID('11cca7fc-507d-4c13-9f51-2810f6e5556e'), 'System Design Interview Vol. 2', 'By Alex Xu. Step-by-step framework for solving system design problems. Covers 13 real-world systems. 2nd edition.', 39.99, 'books', 'BOOK-SDI2-001', 180, True, UUID('9f33bc4c-57d7-4455-a359-4fb29372c4a8'), 'AI Engineering by Chip Huyen', 'Building applications with foundation models. Covers RAG, agents, evaluation, deployment, and production AI systems.', 49.99, 'books', 'BOOK-AIEH-001', 120, True, UUID('8c117643-10f1-40ba-932e-1178694a7886'), 'LAMY Safari Fountain Pen', 'Iconic triangular grip design. Medium nib, ABS body in Mango color. Includes T10 blue ink cartridge. Made in Germany.', 29.99, 'books', 'BOOK-LSFP-001', 300, True, UUID('59304a54-9097-432d-9bdd-35b2bfd86015'), 'Leuchtturm1917 A5 Notebook', '251 numbered dot-grid pages, table of contents, two bookmark ribbons, expandable pocket. Perfect for bullet journaling.', 24.99, 'books', 'BOOK-LT17-001', 250, True, UUID('9bdef35a-eafd-414d-9dce-a377d3e3ff59'), 'Atomic Habits by James Clear', 'Practical strategies for building good habits and breaking bad ones. Over 15 million copies sold. The definitive guide to behavior change.', 18.99, 'books', 'BOOK-AHAB-001', 500, True)
2026-07-24 22:46:52,902 INFO sqlalchemy.engine.Engine INSERT INTO users (id, name, email) VALUES ($1::UUID, $2::VARCHAR, $3::VARCHAR), ($4::UUID, $5::VARCHAR, $6::VARCHAR), ($7::UUID, $8::VARCHAR, $9::VARCHAR), ($10::UUID, $11::VARCHAR, $12::VARCHAR), ($13::UUID, $14::VARCHAR, $15::VARCHAR) RETURNING users.created_at, users.updated_at, users.id
2026-07-24 22:46:52,902 INFO sqlalchemy.engine.Engine [generated in 0.00007s (insertmanyvalues) 1/1 (ordered)] (UUID('12c2b24e-e947-496e-a138-e64768d3440a'), 'Arjun Sharma', 'arjun@example.com', UUID('cc7e021e-ea0b-4720-90ae-e8f88a2dfb66'), 'Priya Patel', 'priya@example.com', UUID('83833e83-e669-45a3-a297-bd26e9f34efb'), 'Rohit Verma', 'rohit@example.com', UUID('e2af7ce5-7dcf-44b7-8f56-222d2cb84bcf'), 'Sneha Reddy', 'sneha@example.com', UUID('768518c2-68ab-4269-86c2-8d86f0d8038d'), 'Vikram Nair', 'vikram@example.com')
2026-07-24 22:46:52,905 INFO sqlalchemy.engine.Engine INSERT INTO orders (id, user_id, status, total_amount, items) VALUES ($1::UUID, $2::UUID, $3::VARCHAR, $4::NUMERIC(10, 2), $5::JSONB), ($6::UUID, $7::UUID, $8::VARCHAR, $9::NUMERIC(10, 2), $10::JSONB), ($11::UUID, $12::UUID, $13::VARCHAR, $14::NUMERI ... 689 characters truncated ... :VARCHAR, $64::NUMERIC(10, 2), $65::JSONB) RETURNING orders.created_at, orders.updated_at, orders.id
2026-07-24 22:46:52,907 INFO sqlalchemy.engine.Engine [generated in 0.00017s (insertmanyvalues) 1/1 (ordered)] (UUID('698903b9-f975-42f1-8126-e39690c4b3da'), UUID('12c2b24e-e947-496e-a138-e64768d3440a'), 'delivered', Decimal('1299.99'), '[{"product_name": "iPhone 16 Pro Max", "qty": 1, "price": 1199.99}]', UUID('c9db613e-4626-4856-9089-08d658e78d29'), UUID('12c2b24e-e947-496e-a138-e64768d3440a'), 'shipped', Decimal('349.99'), '[{"product_name": "Sony WH-1000XM5 Headphones", "qty": 1, "price": 349.99}]', UUID('d11cf6d4-c405-4467-b650-a11da52b7517'), UUID('12c2b24e-e947-496e-a138-e64768d3440a'), 'pending', Decimal('99.99'), '[{"product_name": "Logitech MX Master 3S Mouse", "qty": 1, "price": 99.99}]', UUID('1b6945e9-5894-4f86-8455-024c48496a1e'), UUID('cc7e021e-ea0b-4720-90ae-e8f88a2dfb66'), 'delivered', Decimal('120.0'), '[{"product_name": "Manduka PRO Yoga Mat", "qty": 1, "price": 120.0}]', UUID('1c76e8c6-8c8b-46bb-bb6d-9a05d80072d1'), UUID('cc7e021e-ea0b-4720-90ae-e8f88a2dfb66'), 'delivered', Decimal('63.98'), '[{"product_name": "Atomic Habits by James Clear", "qty": 2, "price": 18.99}, {"product_name": "Leuchtturm1917 A5 Notebook", "qty": 1, "price": 24.99}]', UUID('e3a7b413-3137-4752-9ae3-3b900720ccd7'), UUID('cc7e021e-ea0b-4720-90ae-e8f88a2dfb66'), 'cancelled', Decimal('499.99'), '[{"product_name": "Theragun PRO Plus", "qty": 1, "price": 499.99}]', UUID('68c0ff16-d801-43ca-babb-b4bfc7e50f9c'), UUID('83833e83-e669-45a3-a297-bd26e9f34efb'), 'shipped', Decimal('2499.99'), '[{"product_name": "MacBook Pro 16-inch M3 Max", "qty": 1, "price": 2499.99}]', UUID('661c095c-3b9d-46ae-89af-31e763924110'), UUID('83833e83-e669-45a3-a297-bd26e9f34efb'), 'delivered', Decimal('619.99'), '[{"product_name": "Dell UltraSharp 27 4K Monitor", "qty": 1, "price": 619.99}]', UUID('955a37ce-4c81-4526-b6d0-ad36f6a6b2d7'), UUID('83833e83-e669-45a3-a297-bd26e9f34efb'), 'pending', Decimal('44.99'), '[{"product_name": "Designing Data-Intensive Applications", "qty": 1, "price": 44.99}]', UUID('7091e73f-0482-4948-bf4b-bab79e658c6b'), UUID('e2af7ce5-7dcf-44b7-8f56-222d2cb84bcf'), 'delivered', Decimal('749.99'), '[{"product_name": "Dyson V15 Detect Vacuum", "qty": 1, "price": 749.99}]', UUID('ff7bb652-3e90-46cb-b1b9-c2bd8b746c24'), UUID('e2af7ce5-7dcf-44b7-8f56-222d2cb84bcf'), 'pending', Decimal('999.99'), '[{"product_name": "Dyson Purifier Big Quiet Formaldehyde", "qty": 1, "price": 999.99}]', UUID('6ff59a2f-9083-4f85-ab5a-dfd212bb7a48'), UUID('768518c2-68ab-4269-86c2-8d86f0d8038d'), 'delivered', Decimal('429.99'), '[{"product_name": "Bowflex SelectTech 552 Dumbbells", "qty": 1, "price": 429.99}]', UUID('0e577d59-a122-48e8-ab4c-da7270b422c0'), UUID('768518c2-68ab-4269-86c2-8d86f0d8038d'), 'shipped', Decimal('3495.0'), '[{"product_name": "Peloton Tread+ Treadmill", "qty": 1, "price": 3495.0}]')
2026-07-24 22:46:52,910 INFO sqlalchemy.engine.Engine COMMIT
2026-07-24 22:46:52 [info     ] Seed complete                  orders=13 products=24 users=5
```

**5. Index the knowledge-base docs into pgvector** (needed for RAG/`search_faq`):

```bash
uv run python -m app.rag.ingest
```

```bash
(backend) 
abhis@Tinku MINGW64 ~/Desktop/abhimart/backend (main)
$ uv run python -m app.rag.ingest
2026-07-24 22:47:25 [info     ] Starting RAG ingestion         docs_dir=C:\Users\abhis\Desktop\abhimart\backend\app\rag\docs
2026-07-24 22:47:25 [info     ] Chunked document               chunks=8 file=product-faqs.md
2026-07-24 22:47:25 [info     ] Chunked document               chunks=5 file=return-policy.md
2026-07-24 22:47:25 [info     ] Chunked document               chunks=4 file=shipping-policy.md
2026-07-24 22:47:25 [info     ] Chunked document               chunks=6 file=warranty-terms.md
2026-07-24 22:47:25 [info     ] Total chunks to index          count=23
2026-07-24 22:47:27 [info     ] Ingestion complete             chunks_indexed=23 collection=abhimart_knowledge_base
```

**6. Start the API:**

```bash
uv run uvicorn app.main:app --reload
```

```bash
(backend) 
abhis@Tinku MINGW64 ~/Desktop/abhimart/backend (main)
$ uv run uvicorn app.main:app --reload
INFO:     Will watch for changes in these directories: ['C:\\Users\\abhis\\Desktop\\abhimart\\backend']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [34560] using WatchFiles
2026-07-24 22:47:44 [info     ] OpenTelemetry enabled          environment=local exporter=otlp metrics_enabled=True metrics_exporter=prometheus service_name=abhimart-backend
INFO:     Started server process [40500]
INFO:     Waiting for application startup.
2026-07-24 22:47:47 [info     ] Starting AbhiMart backend      version=0.1.0
2026-07-24 22:47:47,957 INFO sqlalchemy.engine.Engine select pg_catalog.version()
2026-07-24 22:47:47,957 INFO sqlalchemy.engine.Engine [raw sql] ()
2026-07-24 22:47:47,959 INFO sqlalchemy.engine.Engine select current_schema()
2026-07-24 22:47:47,959 INFO sqlalchemy.engine.Engine [raw sql] ()
2026-07-24 22:47:47,962 INFO sqlalchemy.engine.Engine show standard_conforming_strings
2026-07-24 22:47:47,962 INFO sqlalchemy.engine.Engine [raw sql] ()
2026-07-24 22:47:47,964 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2026-07-24 22:47:47,964 INFO sqlalchemy.engine.Engine SELECT 1
2026-07-24 22:47:47,964 INFO sqlalchemy.engine.Engine [generated in 0.00020s] ()
2026-07-24 22:47:47,967 INFO sqlalchemy.engine.Engine COMMIT
2026-07-24 22:47:47 [info     ] Database connection verified  
2026-07-24 22:47:48 [info     ] LangGraph checkpointer ready  
INFO:     Application startup complete.
```

**Then open:**

- **<http://127.0.0.1:8000/docs>** — Swagger UI
- **<http://127.0.0.1:8000/static/chat.html>** — the simple chat UI to actually talk to the agent
- **<http://127.0.0.1:8000/health>** — health check
