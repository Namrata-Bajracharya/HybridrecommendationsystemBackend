"""Seeder to populate category hierarchy with type/origin/design/pattern fields.

Usage:
    python -m app.utils.seed_categories
"""
from app.db.database import SessionLocal
from app.crud.category import CategoryCrud
from app.schema.category_schema import CreateCategory

PATTERNS = ["solid", "printed", "embroidered", "block-print", "bandhani", "ikat", "woven", "patola"]

SWITCH_TYPES = ["linear", "tactile", "clicky", "optical"]
MOUSE_CONNECTIVITY = ["wired", "wireless", "bluetooth", "dual-mode"]


CATEGORIES = [
    {
        "root": "Clothes",
        "description": "All clothing categories",
        "subs": [
            {
                "name": "kurtha",
                "desc": "Traditional and modern kurthas",
                "type": ["casual kurtha", "festive kurtha"],
                "origin": ["jaipur", "north", "telangana", "south"],
                "design": ["casual", "festive", "office", "party"],
                "pattern": PATTERNS,
                "pattern_label": "Pattern",
            },
            {
                "name": "saree",
                "desc": "Elegant sarees from across India",
                "type": ["casual saree", "festive saree", "party saree", "wedding saree"],
                "origin": ["banarasi", "kanchipuram", "chanderi", "jaipur", "gujarat", "rajasthan", "north"],
                "design": ["casual", "festive", "party", "wedding", "office"],
                "pattern": PATTERNS,
                "pattern_label": "Pattern",
            },
            {
                "name": "lehenga",
                "desc": "Beautiful lehengas for celebrations",
                "type": ["wedding lehenga", "festive lehenga"],
                "origin": ["banarasi", "north"],
                "design": ["wedding", "festive"],
                "pattern": PATTERNS,
                "pattern_label": "Pattern",
            },
            {
                "name": "dupatta",
                "desc": "Stylish dupattas to complete your look",
                "type": ["casual dupatta", "party dupatta"],
                "origin": ["north", "gujarat"],
                "design": ["casual", "party", "festive"],
                "pattern": PATTERNS,
                "pattern_label": "Pattern",
            },
        ],
    },
    {
        "root": "Electronics",
        "description": "All electronics categories",
        "subs": [
            {
                "name": "keyboard",
                "desc": "Mechanical, membrane and gaming keyboards",
                "type": ["mechanical", "membrane", "gaming", "ergonomic", "wireless"],
                "origin": ["Logitech", "Razer", "Corsair", "Keychron", "Ducky", "Royal Kludge", "Redragon", "HyperX"],
                "design": ["full-size", "TKL", "60%", "75%", "compact"],
                "pattern": SWITCH_TYPES,
                "pattern_label": "Switch Type",
            },
            {
                "name": "mouse",
                "desc": "Gaming, office and ergonomic mice",
                "type": ["gaming", "office", "ergonomic", "portable"],
                "origin": ["Logitech", "Razer", "Corsair", "HyperX", "SteelSeries", "Redragon"],
                "design": ["ambidextrous", "right-handed", "vertical"],
                "pattern": MOUSE_CONNECTIVITY,
                "pattern_label": "Connectivity",
            },
            {
                "name": "headphone",
                "desc": "Wired and wireless headphones",
                "type": ["over-ear", "on-ear", "in-ear", "gaming headset"],
                "origin": ["Sony", "Bose", "Sennheiser", "Audio-Technica", "HyperX", "Razer", "Logitech"],
                "design": ["closed-back", "open-back", "noise-cancelling", "foldable"],
                "pattern": MOUSE_CONNECTIVITY,
                "pattern_label": "Connectivity",
            },
            {
                "name": "speaker",
                "desc": "Bookshelf and portable speakers",
                "type": ["bookshelf", "portable", "soundbar", "subwoofer"],
                "origin": ["JBL", "Bose", "Sony", "Marshall", "Logitech", "Edifier"],
                "design": ["2.0", "2.1", "5.1", "stereo"],
                "pattern": ["bluetooth", "wifi", "aux", "usb", "hdmi"],
                "pattern_label": "Connectivity",
            },
            {
                "name": "monitor",
                "desc": "Monitors for work and gaming",
                "type": ["gaming", "professional", "ultrawide", "portable", "office"],
                "origin": ["Dell", "Samsung", "LG", "ASUS", "BenQ", "Acer", "Gigabyte"],
                "design": ["1080p", "1440p", "4K", "curved", "flat"],
                "pattern": ["60Hz", "75Hz", "144Hz", "165Hz", "240Hz"],
                "pattern_label": "Refresh Rate",
            },
            {
                "name": "tv",
                "desc": "LED, OLED and smart televisions",
                "type": ["LED", "OLED", "QLED", "Smart TV", "4K"],
                "origin": ["Samsung", "LG", "Sony", "TCL", "Hisense", "Panasonic", "Xiaomi"],
                "design": ["flat", "curved", "ultra-slim", "The Frame"],
                "pattern": ["32\"", "43\"", "55\"", "65\"", "75\"", "85\""],
                "pattern_label": "Screen Size",
            },
            {
                "name": "computer",
                "desc": "Desktop computers and all-in-ones",
                "type": ["gaming desktop", "business desktop", "all-in-one", "mini PC", "workstation"],
                "origin": ["Dell", "HP", "Lenovo", "Apple", "ASUS", "Acer"],
                "design": ["tower", "SFF", "all-in-one", "mini"],
                "pattern": ["Intel Core i3", "Intel Core i5", "Intel Core i7", "AMD Ryzen 5", "AMD Ryzen 7", "Apple M3"],
                "pattern_label": "Processor",
            },
            {
                "name": "motherboard",
                "desc": "Motherboards for all builds",
                "type": ["gaming", "mainstream", "workstation", "budget", "server"],
                "origin": ["ASUS", "Gigabyte", "MSI", "ASRock", "Intel"],
                "design": ["ATX", "micro-ATX", "mini-ITX", "E-ATX"],
                "pattern": ["LGA1700", "AM5", "LGA1200", "AM4", "sTR5"],
                "pattern_label": "Socket",
            },
        ],
    },
    {
        "root": "Sports",
        "description": "Sports equipment and gear",
        "subs": [
            {
                "name": "cricket",
                "desc": "Cricket bats, balls, pads and gear",
                "type": ["bat", "ball", "pads", "gloves", "helmet", "kit bag"],
                "origin": ["Gray-Nicolls", "Kookaburra", "SG", "MRF", "Gunn & Moore", "Adidas"],
                "design": ["junior", "senior", "professional"],
                "pattern": ["English willow", "Kashmir willow", "leather", "synthetic"],
                "pattern_label": "Material",
            },
            {
                "name": "football",
                "desc": "Football boots, balls and accessories",
                "type": ["ball", "boots", "shin guards", "gloves", "jersey"],
                "origin": ["Nike", "Adidas", "Puma", "Under Armour", "Umbro"],
                "design": ["training", "match", "professional"],
                "pattern": ["Size 3", "Size 4", "Size 5", "adult", "youth"],
                "pattern_label": "Size",
            },
            {
                "name": "badminton",
                "desc": "Rackets, shuttlecocks and net sets",
                "type": ["racket", "shuttlecock", "net", "grip", "bag"],
                "origin": ["Yonex", "Li-Ning", "Victor", "Carlton"],
                "design": ["beginner", "intermediate", "advanced"],
                "pattern": ["steel", "aluminum", "carbon fiber", "titanium"],
                "pattern_label": "Frame Material",
            },
            {
                "name": "basketball",
                "desc": "Basketballs, shoes and hoops",
                "type": ["ball", "shoes", "jersey", "hoop", "accessories"],
                "origin": ["Nike", "Adidas", "Spalding", "Wilson"],
                "design": ["indoor", "outdoor", "official"],
                "pattern": ["Size 5", "Size 6", "Size 7", "youth", "adult"],
                "pattern_label": "Size",
            },
            {
                "name": "swimming",
                "desc": "Swimwear, goggles and pool gear",
                "type": ["swimwear", "goggles", "cap", "fins", "accessories"],
                "origin": ["Speedo", "Arena", "TYR", "Nike"],
                "design": ["training", "competition", "recreational"],
                "pattern": ["men", "women", "unisex", "kids"],
                "pattern_label": "Category",
            },
        ],
    },
    {
        "root": "Books",
        "description": "Books across all genres and formats",
        "subs": [
            {
                "name": "fiction",
                "desc": "Novels, short stories and literary fiction",
                "type": ["hardcover", "paperback", "audiobook", "ebook", "box set"],
                "origin": ["Penguin Random House", "HarperCollins", "Simon & Schuster", "Hachette"],
                "design": ["literary", "romance", "thriller", "sci-fi", "fantasy", "horror"],
                "pattern": ["English", "Hindi", "bilingual"],
                "pattern_label": "Language",
            },
            {
                "name": "nonfiction",
                "desc": "Biographies, self-help, history and more",
                "type": ["hardcover", "paperback", "audiobook", "ebook"],
                "origin": ["Penguin", "HarperCollins", "Pan Macmillan", "Bloomsbury"],
                "design": ["biography", "self-help", "history", "science", "business"],
                "pattern": ["English", "Hindi", "bilingual"],
                "pattern_label": "Language",
            },
            {
                "name": "academic",
                "desc": "Textbooks, references and study guides",
                "type": ["textbook", "reference", "workbook", "guide"],
                "origin": ["Oxford", "Cambridge", "McGraw-Hill", "Pearson", "Wiley"],
                "design": ["science", "mathematics", "humanities", "engineering"],
                "pattern": ["English", "Hindi"],
                "pattern_label": "Language",
            },
            {
                "name": "children",
                "desc": "Books for young readers",
                "type": ["board book", "picture book", "chapter book", "activity book"],
                "origin": ["Penguin", "Scholastic", "Walker Books", "Macmillan"],
                "design": ["early learning", "story book", "educational", "rhymes"],
                "pattern": ["0-3 years", "3-5 years", "5-8 years", "8-12 years"],
                "pattern_label": "Age Group",
            },
            {
                "name": "comics",
                "desc": "Graphic novels, manga and comic books",
                "type": ["graphic novel", "manga", "comic book", "webcomic collection"],
                "origin": ["Marvel", "DC", "Dark Horse", "Viz Media", "Image Comics"],
                "design": ["superhero", "slice-of-life", "fantasy", "sci-fi"],
                "pattern": ["English", "Japanese (translated)"],
                "pattern_label": "Language",
            },
        ],
    },
    {
        "root": "Home & Kitchen",
        "description": "Furniture, cookware, decor and appliances",
        "subs": [
            {
                "name": "furniture",
                "desc": "Sofas, beds, tables and chairs",
                "type": ["sofa", "bed", "table", "chair", "cabinet", "bookshelf"],
                "origin": ["IKEA", "Godrej", "Urban Ladder", "Pepperfry"],
                "design": ["modern", "traditional", "minimalist", "industrial"],
                "pattern": ["wood", "metal", "engineered wood", "upholstered"],
                "pattern_label": "Material",
            },
            {
                "name": "cookware",
                "desc": "Pans, pots and kitchen utensils",
                "type": ["pan", "pot", "utensil", "knife", "bakeware"],
                "origin": ["Prestige", "Hawkins", "Pigeon", "Tupperware", "Cello"],
                "design": ["non-stick", "stainless steel", "cast iron", "ceramic"],
                "pattern": ["1-piece", "2-piece", "3-piece", "set"],
                "pattern_label": "Set",
            },
            {
                "name": "decor",
                "desc": "Wall art, vases and decorative items",
                "type": ["wall art", "vases", "figurines", "clock", "candle"],
                "origin": ["Craft", "Clay", "Handicraft"],
                "design": ["traditional", "modern", "bohemian", "vintage"],
                "pattern": ["small", "medium", "large"],
                "pattern_label": "Size",
            },
            {
                "name": "lighting",
                "desc": "Ceiling lights, lamps and bulbs",
                "type": ["ceiling light", "table lamp", "floor lamp", "wall light"],
                "origin": ["Philips", "Havells", "Wipro", "Crompton"],
                "design": ["contemporary", "classic", "industrial", "rustic"],
                "pattern": ["warm white", "cool white", "RGB", "dimmable"],
                "pattern_label": "Light",
            },
            {
                "name": "appliances",
                "desc": "Refrigerators, washing machines and more",
                "type": ["refrigerator", "washing machine", "microwave", "AC", "vacuum"],
                "origin": ["Samsung", "LG", "Whirlpool", "Godrej", "Voltas"],
                "design": ["smart", "inverter", "standard", "portable"],
                "pattern": ["compact", "mid-size", "full-size", "large"],
                "pattern_label": "Capacity",
            },
        ],
    },
    {
        "root": "Beauty",
        "description": "Skincare, makeup, haircare and fragrances",
        "subs": [
            {
                "name": "skincare",
                "desc": "Moisturizers, serums and cleansers",
                "type": ["moisturizer", "serum", "sunscreen", "cleanser", "toner"],
                "origin": ["OLAY", "Neutrogena", "Lakmé", "Cetaphil", "The Ordinary"],
                "design": ["normal", "dry", "oily", "combination", "sensitive"],
                "pattern": ["50ml", "100ml", "200ml"],
                "pattern_label": "Size",
            },
            {
                "name": "makeup",
                "desc": "Foundations, lipsticks and eye makeup",
                "type": ["foundation", "lipstick", "mascara", "eyeshadow", "blush"],
                "origin": ["MAC", "Maybelline", "Lakmé", "NYX", "Huda Beauty"],
                "design": ["matte", "glossy", "shimmer", "natural"],
                "pattern": ["light", "medium", "dark"],
                "pattern_label": "Shade",
            },
            {
                "name": "haircare",
                "desc": "Shampoos, conditioners and hair oils",
                "type": ["shampoo", "conditioner", "hair oil", "serum", "hair mask"],
                "origin": ["Dove", "Pantene", "L'Oréal", "Tresemme", "Moroccanoil"],
                "design": ["normal", "dry", "oily", "damaged", "colored"],
                "pattern": ["200ml", "400ml", "1L"],
                "pattern_label": "Size",
            },
            {
                "name": "fragrance",
                "desc": "Perfumes, deodorants and body sprays",
                "type": ["perfume", "deodorant", "body spray", "roll-on"],
                "origin": ["Chanel", "Dior", "Calvin Klein", "Davidoff", "Axe"],
                "design": ["floral", "woody", "citrus", "oriental", "fresh"],
                "pattern": ["30ml", "50ml", "100ml"],
                "pattern_label": "Size",
            },
            {
                "name": "bath_body",
                "desc": "Body washes, soaps and lotions",
                "type": ["body wash", "soap", "lotion", "scrub", "hand cream"],
                "origin": ["Dove", "Nivea", "Vaseline", "St. Ives", "The Body Shop"],
                "design": ["moisturizing", "exfoliating", "refreshing", "nourishing"],
                "pattern": ["250ml", "500ml", "750ml"],
                "pattern_label": "Size",
            },
        ],
    },
    {
        "root": "Automotive",
        "description": "Car accessories, tools, fluids and gear",
        "subs": [
            {
                "name": "car_accessories",
                "desc": "Dash cams, chargers and seat covers",
                "type": ["dash cam", "phone holder", "charger", "seat cover", "steering cover"],
                "origin": ["3M", "Philips", "Moto", "Autoflip"],
                "design": ["universal", "model-specific", "premium"],
                "pattern": ["black", "beige", "red", "grey"],
                "pattern_label": "Color",
            },
            {
                "name": "motorcycle_gear",
                "desc": "Helmets, gloves and riding jackets",
                "type": ["helmet", "gloves", "jacket", "knee guard", "boots"],
                "origin": ["Studds", "Vega", "Royal Enfield", "LS2", "Axor"],
                "design": ["full face", "open face", "half face", "modular"],
                "pattern": ["M", "L", "XL", "XXL"],
                "pattern_label": "Size",
            },
            {
                "name": "tools",
                "desc": "Wrenches, screwdrivers and tool kits",
                "type": ["wrench", "screwdriver", "hammer", "pliers", "tool kit"],
                "origin": ["Stanley", "Taparia", "Bosch", "Makita"],
                "design": ["manual", "electric", "battery-powered"],
                "pattern": ["6-piece", "12-piece", "24-piece", "48-piece"],
                "pattern_label": "Set",
            },
            {
                "name": "fluids",
                "desc": "Engine oils, coolants and brake fluids",
                "type": ["engine oil", "coolant", "brake fluid", "windshield washer"],
                "origin": ["Castrol", "Mobil", "Shell", "Gulf"],
                "design": ["petrol", "diesel", "synthetic", "semi-synthetic"],
                "pattern": ["1L", "3L", "5L"],
                "pattern_label": "Capacity",
            },
            {
                "name": "interior",
                "desc": "Floor mats, air fresheners and organizers",
                "type": ["floor mat", "air freshener", "organizer", "sun shade"],
                "origin": ["3M", "Ambi Pur", "Godrej"],
                "design": ["basic", "premium", "designer"],
                "pattern": ["front set", "full set"],
                "pattern_label": "Set",
            },
        ],
    },
    {
        "root": "Toys & Games",
        "description": "Action figures, board games, puzzles and more",
        "subs": [
            {
                "name": "action_figures",
                "desc": "Superhero, anime and collectible figures",
                "type": ["superhero", "anime", "collectible", "playset"],
                "origin": ["Marvel", "DC", "Bandai", "Hasbro", "Mattel"],
                "design": ["articulated", "statue", "limited edition"],
                "pattern": ["4-inch", "6-inch", "12-inch"],
                "pattern_label": "Size",
            },
            {
                "name": "board_games",
                "desc": "Strategy, party and family board games",
                "type": ["strategy", "party", "family", "card game"],
                "origin": ["Hasbro", "Mattel", "Funskool", "Ravensburger"],
                "design": ["2-player", "4-player", "6-player", "8-player"],
                "pattern": ["ages 3+", "6+", "8+", "12+", "18+"],
                "pattern_label": "Age",
            },
            {
                "name": "puzzles",
                "desc": "Jigsaw, 3D and logic puzzles",
                "type": ["jigsaw", "3D", "crossword", "logic puzzle"],
                "origin": ["Ravensburger", "Funskool", "Frank"],
                "design": ["landscape", "animals", "abstract", "educational"],
                "pattern": ["100 pieces", "500 pieces", "1000 pieces"],
                "pattern_label": "Pieces",
            },
            {
                "name": "outdoor_toys",
                "desc": "Bicycles, scooters and outdoor play",
                "type": ["bicycle", "scooter", "skateboard", "frisbee", "kite"],
                "origin": ["Hero", "BSA", "Decathlon"],
                "design": ["kids", "youth", "adult"],
                "pattern": ["basic", "mid-range", "premium"],
                "pattern_label": "Range",
            },
            {
                "name": "educational",
                "desc": "STEM kits, flashcards and learning toys",
                "type": ["STEM kit", "flash cards", "activity book", "globe"],
                "origin": ["Funskool", "Frank", "LeapFrog", "VTech"],
                "design": ["science", "math", "language", "geography"],
                "pattern": ["ages 3-5", "5-8", "8-12", "12+"],
                "pattern_label": "Age",
            },
        ],
    },
    {
        "root": "Groceries",
        "description": "Snacks, beverages, staples and organic foods",
        "subs": [
            {
                "name": "snacks",
                "desc": "Chips, biscuits, namkeen and ready-to-eat",
                "type": ["chips", "biscuits", "namkeen", "cookies", "ready-to-eat"],
                "origin": ["Lays", "Parle", "Britannia", "Haldiram", "Kurkure", "Bikaji"],
                "design": ["packed", "family pack", "party pack"],
                "pattern": ["50g", "100g", "200g", "500g", "1kg"],
                "pattern_label": "Weight",
            },
            {
                "name": "beverages",
                "desc": "Tea, coffee, juices and soft drinks",
                "type": ["tea", "coffee", "fruit juice", "soft drink", "energy drink"],
                "origin": ["Tata", "Nestlé", "Coca-Cola", "Pepsi", "Red Bull", "Dabur"],
                "design": ["regular", "sugar-free", "premium"],
                "pattern": ["250ml", "500ml", "1L", "2L"],
                "pattern_label": "Size",
            },
            {
                "name": "staples",
                "desc": "Rice, flour, oil, pulses and spices",
                "type": ["rice", "flour", "cooking oil", "pulses", "spices", "sugar"],
                "origin": ["Fortune", "Aashirvaad", "Tata Sampann", "Patanjali"],
                "design": ["premium", "standard", "organic"],
                "pattern": ["500g", "1kg", "5kg", "10kg"],
                "pattern_label": "Weight",
            },
            {
                "name": "dairy",
                "desc": "Milk, curd, butter, cheese and paneer",
                "type": ["milk", "curd", "butter", "cheese", "paneer"],
                "origin": ["Amul", "Mother Dairy", "Nestlé", "Britannia"],
                "design": ["full cream", "toned", "skimmed", "organic"],
                "pattern": ["200ml", "500ml", "1L"],
                "pattern_label": "Size",
            },
            {
                "name": "organic",
                "desc": "Certified organic and natural products",
                "type": ["grains", "spices", "oils", "superfoods", "honey"],
                "origin": ["24 Mantra", "Patanjali", "Organic India", "Sattviko"],
                "design": ["certified organic", "natural", "wild-crafted"],
                "pattern": ["250g", "500g", "1kg"],
                "pattern_label": "Weight",
            },
        ],
    },
]


def _seed_category_tree(db, crud, root_name, root_desc, subs):
    root = crud.get_category_by_slug(root_name.lower().replace(" ", "_").replace("&", "and"))
    if not root:
        dto = CreateCategory(name=root_name, description=root_desc, fields=None)
        cat = crud.create_category(dto)
        root = crud.get_category_by_id(cat.id)
        print(f"Created root: {root_name} (id={root.id})")
    else:
        print(f"Root {root_name} already exists (id={root.id})")

    for sub in subs:
        slug = sub["name"].lower()
        existing = crud.get_category_by_slug(slug)
        if existing:
            print(f"  Sub '{sub['name']}' already exists, skipping")
            continue

        type_field = {
            "name": sub["name"] + "_type",
            "label": sub["name"].replace("_", " ").title() + " Type",
            "type": "select",
            "options": sub["type"],
            "required": True,
        }

        origin_field = {
            "name": "origin_" + sub["name"],
            "label": "Brand" if root_name == "Electronics" else "Origin",
            "type": "select",
            "options": sub["origin"],
            "belongs_to_type": type_field["name"],
            "required": True,
        }

        design_field = {
            "name": "design_" + sub["name"],
            "label": sub["name"].replace("_", " ").title() + " Design",
            "type": "select",
            "options": sub["design"],
            "belongs_to_type": type_field["name"],
            "belongs_to_origin": origin_field["name"],
            "required": True,
        }

        pattern_field = {
            "name": "design_pattern_" + sub["name"],
            "label": sub["pattern_label"],
            "type": "select",
            "options": sub["pattern"],
            "belongs_to_type": type_field["name"],
            "belongs_to_origin": origin_field["name"],
            "required": False,
        }

        fields = [type_field, origin_field, design_field, pattern_field]

        dto = CreateCategory(
            name=sub["name"],
            parent_id=root.id,
            description=sub["desc"],
            fields=fields,
        )
        created = crud.create_category(dto)
        print(f"  Created sub: {created.name} (id={created.id})")


def seed():
    db = SessionLocal()
    crud = CategoryCrud(db)

    for cat in CATEGORIES:
        _seed_category_tree(db, crud, cat["root"], cat["description"], cat["subs"])

    db.close()
    print("\nSeeding complete!")


if __name__ == "__main__":
    seed()
