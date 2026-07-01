"""Seeder to populate category hierarchy with type/origin/design/pattern fields.

Usage:
    python -m app.utils.seed_categories
"""
from app.db.database import SessionLocal
from app.crud.category import CategoryCrud
from app.schema.category_schema import CreateCategory

PATTERNS = ["solid", "printed", "embroidered", "block-print", "bandhani", "ikat", "woven", "patola"]

SUBS = [
    {
        "name": "kurtha",
        "description": "Traditional and modern kurthas",
        "type_options": ["casual kurtha", "festive kurtha"],
        "origin_options": ["jaipur", "north", "telangana", "south"],
        "design_options": ["casual", "festive", "office", "party"],
    },
    {
        "name": "saree",
        "description": "Elegant sarees from across India",
        "type_options": ["casual saree", "festive saree", "party saree", "wedding saree"],
        "origin_options": ["banarasi", "kanchipuram", "chanderi", "jaipur", "gujarat", "rajasthan", "north"],
        "design_options": ["casual", "festive", "party", "wedding", "office"],
    },
    {
        "name": "lehenga",
        "description": "Beautiful lehengas for celebrations",
        "type_options": ["wedding lehenga", "festive lehenga"],
        "origin_options": ["banarasi", "north"],
        "design_options": ["wedding", "festive"],
    },
    {
        "name": "dupatta",
        "description": "Stylish dupattas to complete your look",
        "type_options": ["casual dupatta", "party dupatta"],
        "origin_options": ["north", "gujarat"],
        "design_options": ["casual", "party", "festive"],
    },
]


def seed():
    db = SessionLocal()
    crud = CategoryCrud(db)

    root = crud.get_category_by_slug("clothes")
    if not root:
        dto = CreateCategory(name="Clothes", description="All clothing categories", fields=None)
        cat = crud.create_category(dto)
        root = crud.get_category_by_id(cat.id)
        print(f"Created root: Clothes (id={root.id})")
    else:
        print(f"Root Clothes already exists (id={root.id})")

    for sub_data in SUBS:
        sub_slug = sub_data["name"].lower()
        existing = crud.get_category_by_slug(sub_slug)
        if existing:
            print(f"  Sub '{sub_data['name']}' already exists, skipping")
            continue

        type_field = {
            "name": sub_data["name"] + "_type",
            "label": sub_data["name"].title() + " Type",
            "type": "select",
            "options": sub_data["type_options"],
            "required": True,
        }

        origin_field = {
            "name": "origin_" + sub_data["name"],
            "label": sub_data["name"].title() + " Origin",
            "type": "select",
            "options": sub_data["origin_options"],
            "belongs_to_type": type_field["name"],
            "required": True,
        }

        design_field = {
            "name": "design_" + sub_data["name"],
            "label": sub_data["name"].title() + " Design",
            "type": "select",
            "options": sub_data["design_options"],
            "belongs_to_type": type_field["name"],
            "belongs_to_origin": origin_field["name"],
            "required": True,
        }

        pattern_field = {
            "name": "design_pattern_" + sub_data["name"],
            "label": "Pattern",
            "type": "select",
            "options": PATTERNS,
            "belongs_to_type": type_field["name"],
            "belongs_to_origin": origin_field["name"],
            "required": False,
        }

        fields = [type_field, origin_field, design_field, pattern_field]

        dto = CreateCategory(
            name=sub_data["name"],
            parent_id=root.id,
            description=sub_data["description"],
            fields=fields,
        )
        sub = crud.create_category(dto)
        print(f"  Created sub: {sub.name} (id={sub.id})")

    db.close()
    print("\nSeeding complete!")


if __name__ == "__main__":
    seed()
