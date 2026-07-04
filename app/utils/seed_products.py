"""Seeder to generate products for clothes, electronics, sports, and books.

Distribution:
  Clothes (30):       kurtha(8) + saree(8) + lehenga(7) + dupatta(7)
  Electronics (15):   keyboard(3) + mouse(2) + headphone(3) + speaker(2)
                      + monitor(2) + tv(2) + motherboard(1)
  Sports (10):        cricket(2) + football(2) + badminton(2)
                      + basketball(2) + swimming(2)
  Books (10):         fiction(2) + nonfiction(2) + academic(2)
                      + children(2) + comics(2)

Variants (4 sets):
  2 for clothes, 2 for electronics — each group has 1 base-priced + 1 custom-priced.

Usage:
    python -m app.utils.seed_products
"""
import random
from itertools import product as iter_product
from app.db.database import SessionLocal
from app.crud.product import ProductCrud
from app.crud.category import CategoryCrud
from app.crud.variant import VariantCrud
from app.schema.product_schema import ProductCreate
from app.schema.variant_schema import VariantCreate


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

    created = 0
    skipped = 0
    # Keep track of created product IDs per root slug for variant seeding
    product_ids: dict[str, list[int]] = {}

    for root_slug, subs in TARGET_SLUGS.items():
        root = slug_to_root.get(root_slug)
        if not root:
            print(f"  Root '{root_slug}' not found — skipping")
            continue
        product_ids[root_slug] = []

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

                dto = ProductCreate(
                    name=name,
                    description=desc,
                    price=_price_for(root_slug),
                    stock_quantity=random.randint(0, 200),
                    field_values=fvals,
                    category_id=child.id,
                    is_active=True,
                )
                try:
                    prod = prod_crud.create_product(dto)
                    created += 1
                    product_ids[root_slug].append(prod.id)
                except Exception:
                    try:
                        dto.name = f"{name} {random.randint(1, 99)}"
                        prod = prod_crud.create_product(dto)
                        created += 1
                        product_ids[root_slug].append(prod.id)
                    except Exception as e2:
                        print(f"    FAILED: {dto.name} — {e2}")
                        skipped += 1

            print(f"  {child.name} ({root.name}): {count} products")

    db.close()
    print(f"\nDone! Created {created} products, skipped {skipped}.")

    # Return IDs so seed_variants can use them
    return product_ids


def seed_variants(product_ids: dict[str, list[int]] | None = None):
    """Add 4 variant sets: 2 clothes + 2 electronics.

    For each group:
      1st product — all variants use base price (price=None)
      2nd product — some variants have custom prices
    """
    from sqlalchemy import select
    from app.models.product import Product

    db = SessionLocal()
    var_crud = VariantCrud(db)

    if product_ids is None:
        # Fallback: pick any products
        stmt = select(Product).where(Product.is_active == True, Product.stock_quantity > 0)
        products = [p for p in db.scalars(stmt).all() if len(p.variants or []) == 0]
    else:
        # Use tracked IDs
        stmt = select(Product).where(Product.id.in_(
            product_ids.get("clothes", []) + product_ids.get("electronics", [])
        ), Product.stock_quantity > 0)
        products = [p for p in db.scalars(stmt).all() if len(p.variants or []) == 0]

    random.shuffle(products)

    clothes_prods = [p for p in products if p.category and p.category.parent and p.category.parent.slug == "clothes"]
    electronics_prods = [p for p in products if p.category and p.category.parent and p.category.parent.slug == "electronics"]

    if len(clothes_prods) < 2:
        print("  Not enough clothes products for variants")
    else:
        _add_variant_set(var_crud, clothes_prods[0], use_base_price=True)
        _add_variant_set(var_crud, clothes_prods[1], use_base_price=False)

    if len(electronics_prods) < 2:
        print("  Not enough electronics products for variants")
    else:
        _add_variant_set(var_crud, electronics_prods[0], use_base_price=True)
        _add_variant_set(var_crud, electronics_prods[1], use_base_price=False)

    db.close()
    print("Variant seeding done.")


def _add_variant_set(var_crud: VariantCrud, product, use_base_price: bool):
    """Add Color x Size variants to a product."""
    colors = ["Red", "Blue", "Black"]
    sizes = ["S", "M", "L"]
    base = int(product.price)

    price_map = {}
    if use_base_price:
        # All variants use base product price
        for c in colors:
            for s in sizes:
                price_map[(c, s)] = None
    else:
        # Some variants get custom prices
        price_map = {
            ("Red", "S"): None,
            ("Red", "M"): int(base * 1.1),
            ("Red", "L"): None,
            ("Blue", "S"): int(base * 0.9),
            ("Blue", "M"): None,
            ("Blue", "L"): None,
            ("Black", "S"): None,
            ("Black", "M"): int(base * 1.2),
            ("Black", "L"): int(base * 0.85),
        }

    created = 0
    for color in colors:
        for size in sizes:
            attrs = [
                {"name": "Color", "value": color},
                {"name": "Size", "value": size},
            ]
            name = f"{color} / {size}"
            dto = VariantCreate(
                name=name,
                attributes=attrs,
                price=price_map.get((color, size)),
                stock_quantity=random.randint(5, 30),
            )
            try:
                var_crud.create(product.id, dto)
                created += 1
            except Exception as e:
                print(f"    FAILED variant {name}: {e}")

    mode = "base-price" if use_base_price else "custom-price"
    print(f"  Added {created} variants ({mode}) to '{product.name}'")


if __name__ == "__main__":
    pids = seed()
    seed_variants(pids)
