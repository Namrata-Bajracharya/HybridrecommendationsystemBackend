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

# One placeholder image slot per root category (used for all products in that category)
SEED_SLOTS = {
    "clothes":     [{"name": "clothes_1", "rgb": (200, 160, 160)},
                    {"name": "clothes_2", "rgb": (160, 180, 200)}],
    "electronics": [{"name": "electronics_1", "rgb": (180, 190, 210)},
                    {"name": "electronics_2", "rgb": (160, 200, 180)}],
    "sports":      [{"name": "sports_1", "rgb": (200, 190, 150)},
                    {"name": "sports_2", "rgb": (180, 200, 180)}],
    "books":       [{"name": "books_1", "rgb": (180, 160, 140)},
                    {"name": "books_2", "rgb": (190, 180, 200)}],
}


def _make_data_url(rgb: tuple[int, int, int]) -> str:
    """Create a base64 data URL for a solid-colour 800×800 JPEG image."""
    img = Image.new("RGB", (800, 800), rgb)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/jpeg;base64,{b64}"


def _ensure_seed_images() -> dict[str, list[str]]:
    """Generate base64 data URLs for each root slot.

    Returns {root_slug: [data_url, ...]}.
    """
    slot_urls: dict[str, list[str]] = {}
    for root_slug, slots in SEED_SLOTS.items():
        urls = []
        for slot in slots:
            urls.append(_make_data_url(slot["rgb"]))
        slot_urls[root_slug] = urls
    return slot_urls


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

    # Pre-create seed image data URLs
    slot_urls = _ensure_seed_images()

    # Map slug → root
    roots = cat_crud.get_root_categories()
    slug_to_root = {r.slug: r for r in roots}

    created = 0
    skipped = 0

    for root_slug, subs in TARGET_SLUGS.items():
        root = slug_to_root.get(root_slug)
        if not root:
            print(f"  Root '{root_slug}' not found — skipping")
            continue
        root_images = slot_urls.get(root_slug, [])

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
                    image_data_urls=(
                        [random.choice(root_images)]
                        if root_images
                        else None
                    ),
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
