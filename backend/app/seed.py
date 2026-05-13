"""Seed the database with sample product data.

Run with:
    uv run python -m app.seed

Why a separate script (not a route or migration)?
- Migrations handle schema changes (CREATE TABLE, ADD COLUMN)
- Seeds handle data. They're not schema — they're test/demo content.
- A script can be run anytime: fresh setup, after a DB wipe, in CI.

Idempotent: running this twice produces the same result (deletes + re-inserts).
"""

import asyncio

import structlog
from sqlalchemy import delete
import uuid
from decimal import Decimal
from sqlalchemy import delete
from app.models.user import User
from app.models.order import Order
from app.database import async_session_factory
from app.models.product import Product

logger = structlog.get_logger()

# --- Seed Data ---
# Realistic products across all 4 AbhiMart categories.
# Each product has a unique SKU pattern: {CATEGORY_PREFIX}-{PRODUCT_CODE}-{SEQ}

SEED_PRODUCTS = [
    # ==================== ELECTRONICS ====================
    {
        "name": "MacBook Pro 16-inch M3 Max",
        "description": "Apple M3 Max chip, 36GB unified memory, 1TB SSD, 16-inch Liquid Retina XDR display. Perfect for professional video editing and software development.",
        "price": 2499.99,
        "category": "electronics",
        "sku": "ELEC-MBP16-001",
        "stock_quantity": 25,
    },
    {
        "name": "iPhone 16 Pro Max",
        "description": "A18 Pro chip, 6.9-inch Super Retina XDR display, 48MP camera system, titanium design. 256GB storage.",
        "price": 1199.99,
        "category": "electronics",
        "sku": "ELEC-IP16PM-001",
        "stock_quantity": 100,
    },
    {
        "name": "Sony WH-1000XM5 Headphones",
        "description": "Industry-leading noise cancellation, 30-hour battery life, crystal clear hands-free calling. Lightweight and comfortable.",
        "price": 349.99,
        "category": "electronics",
        "sku": "ELEC-SNYWH5-001",
        "stock_quantity": 75,
    },
    {
        "name": "Samsung Galaxy Tab S9 Ultra",
        "description": "14.6-inch Dynamic AMOLED 2X display, Snapdragon 8 Gen 2, 12GB RAM, S Pen included. Great for digital art.",
        "price": 1199.99,
        "category": "electronics",
        "sku": "ELEC-SGTS9U-001",
        "stock_quantity": 40,
    },
    {
        "name": "Logitech MX Master 3S Mouse",
        "description": "Ergonomic wireless mouse with MagSpeed scroll, 8K DPI sensor, USB-C charging. Works on any surface including glass.",
        "price": 99.99,
        "category": "electronics",
        "sku": "ELEC-LMXM3S-001",
        "stock_quantity": 200,
    },
    {
        "name": "Dell UltraSharp 27 4K Monitor",
        "description": "27-inch 4K UHD IPS display, USB-C hub with 90W charging, 98% DCI-P3 color coverage. Factory calibrated.",
        "price": 619.99,
        "category": "electronics",
        "sku": "ELEC-DU274K-001",
        "stock_quantity": 35,
    },
    # ==================== APPLIANCES ====================
    {
        "name": "Instant Pot Pro Plus 6-Quart",
        "description": "10-in-1 pressure cooker: pressure cook, slow cook, sauté, steam, sous vide, and more. Whisper-quiet steam release.",
        "price": 129.99,
        "category": "appliances",
        "sku": "APPL-IPP6Q-001",
        "stock_quantity": 80,
    },
    {
        "name": "Dyson V15 Detect Vacuum",
        "description": "Laser-equipped cordless vacuum that reveals invisible dust. Up to 60 minutes of fade-free power. HEPA filtration.",
        "price": 749.99,
        "category": "appliances",
        "sku": "APPL-DV15D-001",
        "stock_quantity": 45,
    },
    {
        "name": "Dyson Purifier Big Quiet Formaldehyde",
        "description": "Whole-room air purifier for large spaces. HEPA H13 filter captures 99.97% of particles. Destroys formaldehyde continuously.",
        "price": 999.99,
        "category": "appliances",
        "sku": "APPL-DPBQF-001",
        "stock_quantity": 20,
    },
    {
        "name": "KitchenAid Artisan Stand Mixer",
        "description": "5-quart tilt-head stand mixer with 10 speeds. Includes flat beater, dough hook, and wire whip. Empire Red.",
        "price": 449.99,
        "category": "appliances",
        "sku": "APPL-KASM5-001",
        "stock_quantity": 60,
    },
    {
        "name": "Breville Barista Express Espresso Machine",
        "description": "Built-in conical burr grinder, precise espresso extraction, steam wand for microfoam milk. Bean-to-cup in under a minute.",
        "price": 699.99,
        "category": "appliances",
        "sku": "APPL-BBE87-001",
        "stock_quantity": 30,
    },
    {
        "name": "Ninja Foodi Smart XL Grill",
        "description": "6-in-1 indoor grill and air fryer. Smart Cook System with thermometer for perfect doneness. Smoke control system.",
        "price": 279.99,
        "category": "appliances",
        "sku": "APPL-NFXLG-001",
        "stock_quantity": 55,
    },
    # ==================== FITNESS ====================
    {
        "name": "Peloton Tread+ Treadmill",
        "description": "67-inch running surface, incline up to 15%, decline down to -3%. Immersive 32-inch HD touchscreen for live and on-demand classes.",
        "price": 3495.00,
        "category": "fitness",
        "sku": "FIT-PTRDP-001",
        "stock_quantity": 10,
    },
    {
        "name": "Bowflex SelectTech 552 Dumbbells",
        "description": "Adjustable dumbbells replacing 15 sets of weights. Dial from 5 to 52.5 lbs in 2.5 lb increments. Sold as a pair.",
        "price": 429.99,
        "category": "fitness",
        "sku": "FIT-BFS52-001",
        "stock_quantity": 65,
    },
    {
        "name": "Apple Watch Ultra 2",
        "description": "49mm titanium case, precision dual-frequency GPS, up to 36 hours battery life. Water resistant to 100m. Advanced health sensors.",
        "price": 799.99,
        "category": "fitness",
        "sku": "FIT-AWU2-001",
        "stock_quantity": 90,
    },
    {
        "name": "Theragun PRO Plus",
        "description": "Professional-grade percussive therapy device. 6 attachments, Bluetooth app integration, OLED screen. Quiet operation.",
        "price": 499.99,
        "category": "fitness",
        "sku": "FIT-TGPP-001",
        "stock_quantity": 40,
    },
    {
        "name": "Rogue Echo Bike",
        "description": "Heavy-duty fan bike for intense cardio. Belt-driven steel fan, powder-coated steel frame. Supports up to 350 lbs.",
        "price": 795.00,
        "category": "fitness",
        "sku": "FIT-REB-001",
        "stock_quantity": 15,
    },
    {
        "name": "Manduka PRO Yoga Mat",
        "description": "71-inch premium yoga mat, 6mm thick. Closed-cell surface prevents sweat absorption. Lifetime guarantee. Black Magic color.",
        "price": 120.00,
        "category": "fitness",
        "sku": "FIT-MPYM-001",
        "stock_quantity": 150,
    },
    # ==================== BOOKS & STATIONERY ====================
    {
        "name": "Designing Data-Intensive Applications",
        "description": "By Martin Kleppmann. The must-read guide to distributed systems, databases, and data pipelines. Essential for backend engineers.",
        "price": 44.99,
        "category": "books",
        "sku": "BOOK-DDIA-001",
        "stock_quantity": 200,
    },
    {
        "name": "System Design Interview Vol. 2",
        "description": "By Alex Xu. Step-by-step framework for solving system design problems. Covers 13 real-world systems. 2nd edition.",
        "price": 39.99,
        "category": "books",
        "sku": "BOOK-SDI2-001",
        "stock_quantity": 180,
    },
    {
        "name": "AI Engineering by Chip Huyen",
        "description": "Building applications with foundation models. Covers RAG, agents, evaluation, deployment, and production AI systems.",
        "price": 49.99,
        "category": "books",
        "sku": "BOOK-AIEH-001",
        "stock_quantity": 120,
    },
    {
        "name": "LAMY Safari Fountain Pen",
        "description": "Iconic triangular grip design. Medium nib, ABS body in Mango color. Includes T10 blue ink cartridge. Made in Germany.",
        "price": 29.99,
        "category": "books",
        "sku": "BOOK-LSFP-001",
        "stock_quantity": 300,
    },
    {
        "name": "Leuchtturm1917 A5 Notebook",
        "description": "251 numbered dot-grid pages, table of contents, two bookmark ribbons, expandable pocket. Perfect for bullet journaling.",
        "price": 24.99,
        "category": "books",
        "sku": "BOOK-LT17-001",
        "stock_quantity": 250,
    },
    {
        "name": "Atomic Habits by James Clear",
        "description": "Practical strategies for building good habits and breaking bad ones. Over 15 million copies sold. The definitive guide to behavior change.",
        "price": 18.99,
        "category": "books",
        "sku": "BOOK-AHAB-001",
        "stock_quantity": 500,
    },
]

SEED_USERS = [
    {"name": "Arjun Sharma", "email": "arjun@example.com"},
    {"name": "Priya Patel", "email": "priya@example.com"},
    {"name": "Rohit Verma", "email": "rohit@example.com"},
    {"name": "Sneha Reddy", "email": "sneha@example.com"},
    {"name": "Vikram Nair", "email": "vikram@example.com"},
]

SEED_ORDERS = [
    {
        "email": "arjun@example.com",
        "status": "delivered",
        "total": 1299.99,
        "items": [{"product_name": "iPhone 16 Pro Max", "qty": 1, "price": 1199.99}],
    },
    {
        "email": "arjun@example.com",
        "status": "shipped",
        "total": 349.99,
        "items": [
            {"product_name": "Sony WH-1000XM5 Headphones", "qty": 1, "price": 349.99}
        ],
    },
    {
        "email": "arjun@example.com",
        "status": "pending",
        "total": 99.99,
        "items": [
            {"product_name": "Logitech MX Master 3S Mouse", "qty": 1, "price": 99.99}
        ],
    },
    {
        "email": "priya@example.com",
        "status": "delivered",
        "total": 120.00,
        "items": [{"product_name": "Manduka PRO Yoga Mat", "qty": 1, "price": 120.00}],
    },
    {
        "email": "priya@example.com",
        "status": "delivered",
        "total": 63.98,
        "items": [
            {"product_name": "Atomic Habits by James Clear", "qty": 2, "price": 18.99},
            {"product_name": "Leuchtturm1917 A5 Notebook", "qty": 1, "price": 24.99},
        ],
    },
    {
        "email": "priya@example.com",
        "status": "cancelled",
        "total": 499.99,
        "items": [{"product_name": "Theragun PRO Plus", "qty": 1, "price": 499.99}],
    },
    {
        "email": "rohit@example.com",
        "status": "shipped",
        "total": 2499.99,
        "items": [
            {"product_name": "MacBook Pro 16-inch M3 Max", "qty": 1, "price": 2499.99}
        ],
    },
    {
        "email": "rohit@example.com",
        "status": "delivered",
        "total": 619.99,
        "items": [
            {"product_name": "Dell UltraSharp 27 4K Monitor", "qty": 1, "price": 619.99}
        ],
    },
    {
        "email": "rohit@example.com",
        "status": "pending",
        "total": 44.99,
        "items": [
            {
                "product_name": "Designing Data-Intensive Applications",
                "qty": 1,
                "price": 44.99,
            }
        ],
    },
    {
        "email": "sneha@example.com",
        "status": "delivered",
        "total": 749.99,
        "items": [
            {"product_name": "Dyson V15 Detect Vacuum", "qty": 1, "price": 749.99}
        ],
    },
    {
        "email": "sneha@example.com",
        "status": "pending",
        "total": 999.99,
        "items": [
            {
                "product_name": "Dyson Purifier Big Quiet Formaldehyde",
                "qty": 1,
                "price": 999.99,
            }
        ],
    },
    {
        "email": "vikram@example.com",
        "status": "delivered",
        "total": 429.99,
        "items": [
            {
                "product_name": "Bowflex SelectTech 552 Dumbbells",
                "qty": 1,
                "price": 429.99,
            }
        ],
    },
    {
        "email": "vikram@example.com",
        "status": "shipped",
        "total": 3495.00,
        "items": [
            {"product_name": "Peloton Tread+ Treadmill", "qty": 1, "price": 3495.00}
        ],
    },
]


async def seed() -> None:
    """Clear and re-seed all tables."""
    async with async_session_factory() as session:
        # Delete in FK-safe order: orders → users → products
        await session.execute(delete(Order))
        await session.execute(delete(User))
        await session.execute(delete(Product))
        logger.info("Cleared existing data")

        # Seed products
        products = [Product(**data) for data in SEED_PRODUCTS]
        session.add_all(products)

        # Seed users
        users = [User(id=uuid.uuid4(), **u) for u in SEED_USERS]
        session.add_all(users)
        await session.flush()  # need user IDs before creating orders

        # Seed orders
        user_map = {u.email: u.id for u in users}
        orders = [
            Order(
                id=uuid.uuid4(),
                user_id=user_map[o["email"]],
                status=o["status"],
                total_amount=Decimal(str(o["total"])),
                items=o["items"],
            )
            for o in SEED_ORDERS
        ]
        session.add_all(orders)
        await session.commit()

        logger.info(
            "Seed complete",
            products=len(products),
            users=len(users),
            orders=len(orders),
        )


if __name__ == "__main__":
    asyncio.run(seed())
