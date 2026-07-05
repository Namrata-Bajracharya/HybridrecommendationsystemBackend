"""Seeder to generate products for clothes, electronics, sports, and books.

Distribution:
  Clothes (30):       kurtha(8) + saree(8) + lehenga(7) + dupatta(7)
  Electronics (15):   keyboard(3) + mouse(2) + headphone(3) + speaker(2)
                      + monitor(2) + tv(2) + motherboard(1)
  Sports (10):        cricket(2) + football(2) + badminton(2)
                      + basketball(2) + swimming(2)
  Books (10):         fiction(2) + nonfiction(2) + academic(2)
                      + children(2) + comics(2)

Usage:
    python -m app.utils.seed_products
"""
import base64
import io
import random
from itertools import cycle
from PIL import Image
from app.db.database import SessionLocal
from app.crud.product import ProductCrud
from app.crud.category import CategoryCrud
from app.schema.product_schema import ProductCreate


random.seed(42)

PRICE_RANGES = {
    "clothes":     (499, 8999),
    "electronics": (599, 150000),
    "sports":      (199, 25000),
    "books":       (99, 4999),
}

ADJECTIVES = [
    "Premium", "Classic", "Modern", "Elegant", "Ultra", "Pro",
    "Elite", "Essential", "Deluxe", "Superior", "Advanced", "Slim",
    "Compact", "Professional", "Standard", "Portable", "Smart",
]

SEED_SLOTS = {
    "clothes":     (200, 160, 160),
    "electronics": (180, 190, 210),
    "sports":      (200, 190, 150),
    "books":       (180, 160, 140),
}


def _make_data_url(rgb: tuple[int, int, int]) -> str:
    """Create a base64 data URL for a solid-colour 800×800 JPEG image."""
    img = Image.new("RGB", (800, 800), rgb)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/jpeg;base64,{b64}"


def _load_real_document_ids(db) -> list[str]:
    """Return IDs of real product images already in the DB (PNG files)."""
    from app.models.document import Document
    rows = (
        db.query(Document.id)
        .filter(Document.relative_path.like('%.png'))
        .all()
    )
    return [r[0] for r in rows]


def _price_for(root_slug: str) -> float:
    lo, hi = PRICE_RANGES.get(root_slug, (199, 9999))
    p = random.randint(lo, hi)
    return round(p / 10) * 10 - 1 if p > 10 else p


def _pick_options(fields: list[dict]) -> dict[str, str]:
    vals = {}
    for f in (fields or []):
        opts = f.get("options", [])
        if opts:
            vals[f["name"]] = random.choice(opts)
    return vals


def _product_name(sub_name: str, fvals: dict) -> str:
    type_val = None
    origin_val = None
    for k, v in fvals.items():
        if not k.startswith("origin_") and not k.startswith("design_") and not k.startswith("design_pattern_") and not k.startswith("bath_body"):
            type_val = v
        elif k.startswith("origin_"):
            origin_val = v

    adj = random.choice(ADJECTIVES)
    label = sub_name.replace("_", " ").title()

    if type_val and origin_val:
        return f"{adj} {origin_val} {type_val} {label}"
    elif origin_val:
        return f"{adj} {origin_val} {label}"
    elif type_val:
        return f"{adj} {type_val} {label}"
    else:
        return f"{adj} {label}"


_DESCRIPTION_TEMPLATES = [
    "High-quality {name} designed for comfort and style.",
    "Durable and reliable {name} perfect for everyday use.",
    "Experience the best with this premium {name}.",
    "Top-rated {name} with excellent performance and value.",
    "Versatile {name} suitable for all your needs.",
    "Stylish {name} crafted with premium materials.",
    "Upgrade your experience with this {name}.",
    "Professional-grade {name} built to last.",
    "Compact and efficient {name} for modern lifestyles.",
    "Premium {name} with advanced features and elegant design.",
]


def _description(name: str) -> str:
    return random.choice(_DESCRIPTION_TEMPLATES).format(name=name)


def seed():
    db = SessionLocal()
    cat_crud = CategoryCrud(db)
    prod_crud = ProductCrud(db)

    # ── Config: which roots + sub-counts ──
    TARGET_SLUGS = {
        "clothes":     {"kurtha": 8, "saree": 8, "lehenga": 7, "dupatta": 7},
        "electronics": {"keyboard": 3, "mouse": 2, "headphone": 3, "speaker": 2,
                        "monitor": 2, "tv": 2, "motherboard": 1},
        "sports":      {"cricket": 2, "football": 2, "badminton": 2,
                        "basketball": 2, "swimming": 2},
        "books":       {"fiction": 2, "nonfiction": 2, "academic": 2,
                        "children": 2, "comics": 2},
    }

    # Map slug → root
    roots = cat_crud.get_root_categories()
    slug_to_root = {r.slug: r for r in roots}

    # Load real document IDs from DB (PNG = real images uploaded by user)
    real_doc_ids = _load_real_document_ids(db)
    if real_doc_ids:
        print(f"  Using {len(real_doc_ids)} real images from DB")
        doc_cycle = cycle(real_doc_ids)

        def _img_for_product() -> dict:
            return {"image_document_ids": [next(doc_cycle)], "image_data_urls": None}
    else:
        print("  No real images found — generating solid-color placeholders")

        def _img_for_product(r_slug: str) -> dict:
            url = _make_data_url(SEED_SLOTS.get(r_slug, (200, 200, 200)))
            return {"image_data_urls": [url], "image_document_ids": None}

    created = 0
    skipped = 0

    for root_slug, subs in TARGET_SLUGS.items():
        root = slug_to_root.get(root_slug)
        if not root:
            print(f"  Root '{root_slug}' not found — skipping")
            continue

        for sub_name, count in subs.items():
            child = next((c for c in (root.children or []) if c.name == sub_name), None)
            if not child:
                print(f"  Sub-category '{sub_name}' not found under {root.name}")
                continue
            if not child.fields:
                print(f"  Skipping {child.name} — no fields defined")
                continue

            for _ in range(count):
                fvals = _pick_options(child.fields)
                name = _product_name(child.name, fvals)
                desc = _description(name)
                p = _price_for(root_slug)
                bp = round(p * random.uniform(0.4, 0.8), 2)

                kwargs = _img_for_product(root_slug) if not real_doc_ids else _img_for_product()
                dto = ProductCreate(
                    name=name,
                    description=desc,
                    price=p,
                    buying_price=bp,
                    selling_price=p,
                    stock_quantity=random.randint(0, 200),
                    field_values=fvals,
                    category_id=child.id,
                    is_active=True,
                    **kwargs,
                )
                try:
                    prod_crud.create_product(dto)
                    created += 1
                except Exception:
                    try:
                        dto.name = f"{name} {random.randint(1, 99)}"
                        prod_crud.create_product(dto)
                        created += 1
                    except Exception as e2:
                        print(f"    FAILED: {dto.name} — {e2}")
                        skipped += 1

            print(f"  {child.name} ({root.name}): {count} products")

    db.close()
    print(f"\nDone! Created {created} products, skipped {skipped}.")


if __name__ == "__main__":
    seed()
