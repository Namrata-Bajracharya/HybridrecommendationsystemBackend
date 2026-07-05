"""Comprehensive data seeder: creates 45 users with orders, reviews, refunds, etc.

Creates realistic e-commerce data for testing dashboards, recommendation engine,
profit/loss reports, and other features.

Usage:
    python -m app.utils.seed_data
"""

import random
import datetime
from datetime import timedelta

from app.db.database import SessionLocal
from app.utils.security import hash_password
from app.utils.order_utils import generate_order_number, generate_trx_ref
from app.models.user import User
from app.models.address import Address
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.review import Review
from app.models.wishlist import Wishlist
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product import Product

random.seed(42)

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Anaya", "Ishaan",
    "Reyansh", "Siddharth", "Rohan", "Kunal", "Amit", "Ravi", "Suresh",
    "Priya", "Neha", "Riya", "Ananya", "Sneha", "Deepika", "Pooja",
    "Aishwarya", "Kavya", "Divya", "Shruti", "Nandini", "Anjali",
    "Rahul", "Vikas", "Sanjay", "Manoj", "Rajesh", "Rakesh", "Vijay",
    "Ashok", "Dinesh", "Sachin", "Mahesh", "Sunil", "Akash", "Gaurav",
    "Nikhil", "Harsh", "Karan",
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Singh", "Kumar", "Gupta", "Reddy", "Joshi",
    "Das", "Nair", "Menon", "Iyer", "Rao", "Pandey", "Mishra", "Saxena",
    "Agarwal", "Mehta", "Shah", "Chopra", "Malhotra", "Kapoor", "Khanna",
    "Arora", "Bhatia", "Sethi", "Tiwari", "Dubey", "Chauhan", "Yadav",
    "Sinha", "Bose", "Ghosh", "Desai", "Bhatt",
]

CITIES = [
    ("Mumbai", "Mumbai City", "Maharashtra"),
    ("Delhi", "Central Delhi", "Delhi"),
    ("Bangalore", "Bangalore Urban", "Karnataka"),
    ("Hyderabad", "Hyderabad", "Telangana"),
    ("Ahmedabad", "Ahmedabad", "Gujarat"),
    ("Chennai", "Chennai", "Tamil Nadu"),
    ("Kolkata", "Kolkata", "West Bengal"),
    ("Pune", "Pune", "Maharashtra"),
    ("Jaipur", "Jaipur", "Rajasthan"),
    ("Lucknow", "Lucknow", "Uttar Pradesh"),
    ("Surat", "Surat", "Gujarat"),
    ("Indore", "Indore", "Madhya Pradesh"),
    ("Bhopal", "Bhopal", "Madhya Pradesh"),
    ("Chandigarh", "Chandigarh", "Chandigarh"),
    ("Nagpur", "Nagpur", "Maharashtra"),
    ("Patna", "Patna", "Bihar"),
    ("Thiruvananthapuram", "Thiruvananthapuram", "Kerala"),
    ("Coimbatore", "Coimbatore", "Tamil Nadu"),
    ("Guwahati", "Kamrup", "Assam"),
    ("Bhubaneswar", "Khordha", "Odisha"),
]

STREETS = [
    "MG Road", "Park Street", "Lake View Road", "Main Street", "Church Street",
    "Commercial Street", "Banjara Hills Road", "Koregaon Park Road",
    "Marine Drive", "Bandra West", "Connaught Place", "Janpath",
    "Sector 18", "Gandhi Nagar", "Civil Lines", "VIP Road",
    "Salt Lake Sector V", "HBR Layout", "Jayanagar", "Indiranagar",
    "Whitefield Main Road", "Sarjapur Road", "Electronic City Phase 1",
]

REVIEW_COMMENTS = {
    5: [
        "Excellent product! Would buy again.",
        "Very happy with this purchase, quality is top-notch.",
        "Highly recommended! Exceeded my expectations.",
        "Perfect quality and fast delivery. Thank you!",
        "Absolutely love it! Worth every penny.",
    ],
    4: [
        "Great product, minor issues but overall satisfied.",
        "Very good quality for the price point.",
        "Happy with the purchase, works as expected.",
        "Good value for money. Would recommend.",
        "Solid product, does what it's supposed to.",
    ],
    3: [
        "Average product, okay for the price.",
        "Decent quality but could be better.",
        "Not bad, but I've seen better options.",
        "It's fine, nothing special.",
        "Does the job but nothing impressive.",
    ],
    2: [
        "Below expectations, quality could be better.",
        "Not worth the price, unfortunately.",
        "Disappointed with the purchase.",
        "Expected more given the description.",
    ],
    1: [
        "Very poor quality, do not recommend.",
        "Terrible product, complete waste of money.",
        "Completely dissatisfied, want a refund.",
        "Broke within a week of use. Very disappointed.",
    ],
}

ADMIN_REPLIES = [
    "Thank you for your feedback! We're glad you liked the product.",
    "We appreciate your honest review. We'll work on improving.",
    "Thank you for sharing your experience. We value your opinion.",
    "We're sorry to hear that. Please contact our support team for assistance.",
    "Thanks for the review! We hope to serve you again soon.",
    "We take your feedback seriously and will address the issues mentioned.",
]

ORDER_STATUS_WEIGHTS = [
    ("delivered", 35),
    ("rejected", 8),
    ("cancelled", 7),
    ("refund_requested", 5),
    ("refund_successful", 8),
    ("pending", 10),
    ("accepted", 8),
    ("packed", 10),
    ("on_delivery", 9),
]


def _pick_status() -> str:
    statuses = [s for s, w in ORDER_STATUS_WEIGHTS for _ in range(w)]
    return random.choice(statuses)


def seed():
    db = SessionLocal()

    print("Starting comprehensive data seed...")
    print("=" * 50)

    # ── Step 1: Clean existing seed customer data ──
    existing_customers = db.query(User).filter(User.role == "customer").all()
    customer_ids = [u.id for u in existing_customers]

    if customer_ids:
        print(f"Removing {len(customer_ids)} existing customers and related data...")
        db.query(Review).filter(Review.user_id.in_(customer_ids)).delete(synchronize_session=False)
        db.query(CartItem).filter(CartItem.cart_id.in_(
            db.query(Cart.id).filter(Cart.user_id.in_(customer_ids))
        )).delete(synchronize_session=False)
        db.query(Cart).filter(Cart.user_id.in_(customer_ids)).delete(synchronize_session=False)
        db.query(Wishlist).filter(Wishlist.user_id.in_(customer_ids)).delete(synchronize_session=False)
        db.query(OrderItem).filter(OrderItem.order_id.in_(
            db.query(Order.id).filter(Order.user_id.in_(customer_ids))
        )).delete(synchronize_session=False)
        db.query(Payment).filter(Payment.order_id.in_(
            db.query(Order.id).filter(Order.user_id.in_(customer_ids))
        )).delete(synchronize_session=False)
        db.query(Order).filter(Order.user_id.in_(customer_ids)).delete(synchronize_session=False)
        db.query(Address).filter(Address.user_id.in_(customer_ids)).delete(synchronize_session=False)
        db.query(User).filter(User.id.in_(customer_ids)).delete(synchronize_session=False)
        db.commit()
        print("Cleaned existing data.")

    # ── Step 2: Create 45 customer users ──
    print("\nCreating 45 customer users...")
    users = []
    hashed_pw = hash_password("password123")
    used_emails = set()

    for i in range(45):
        fn = random.choice(FIRST_NAMES)
        ln = random.choice(LAST_NAMES)
        base_email = f"{fn.lower()}.{ln.lower()}"
        email = f"{base_email}{i+1}@example.com"
        while email in used_emails:
            email = f"{base_email}{random.randint(100, 999)}@example.com"
        used_emails.add(email)

        phone = f"+91{random.randint(7000000000, 9999999999)}"
        days_ago = random.randint(30, 365)
        created = datetime.datetime.now() - timedelta(days=days_ago)

        user = User(
            email=email,
            password_hash=hashed_pw,
            first_name=fn,
            last_name=ln,
            phone=phone,
            role="customer",
            is_verified=True,
            created_at=created,
        )
        db.add(user)
        db.flush()
        users.append(user)

    db.commit()
    print(f"  Created {len(users)} users")

    # ── Step 3: Create addresses (2 per user) ──
    print("Creating addresses...")
    all_addresses = []
    for user in users:
        city, district, state = random.choice(CITIES)
        street = random.choice(STREETS)
        house = f"{random.randint(1, 999)}/{random.randint(1, 50)}"

        shipping = Address(
            user_id=user.id,
            type="shipping",
            label="Home",
            phone=user.phone,
            street=f"{house}, {street}",
            city=city,
            district=district,
            zone=f"Zone {random.randint(1, 10)}",
            state=state,
            postal_code=str(random.randint(100000, 999999)),
            country="India",
            is_default=True,
        )
        db.add(shipping)
        db.flush()
        all_addresses.append(shipping)

        if random.random() < 0.3:
            city2, district2, state2 = random.choice(CITIES)
            street2 = random.choice(STREETS)
            billing = Address(
                user_id=user.id,
                type="billing",
                label="Office",
                phone=user.phone,
                street=f"{random.randint(1, 999)}, {street2}",
                city=city2,
                district=district2,
                zone=f"Zone {random.randint(1, 10)}",
                state=state2,
                postal_code=str(random.randint(100000, 999999)),
                country="India",
                is_default=False,
            )
        else:
            billing = Address(
                user_id=user.id,
                type="billing",
                label="Office",
                phone=user.phone,
                street=f"{random.randint(1, 999)}, {street}",
                city=city,
                district=district,
                zone=f"Zone {random.randint(1, 10)}",
                state=state,
                postal_code=str(random.randint(100000, 999999)),
                country="India",
                is_default=False,
            )
        db.add(billing)
        db.flush()
        all_addresses.append(billing)

    db.commit()
    print(f"  Created {len(all_addresses)} addresses")

    # ── Step 4: Fetch existing products ──
    products = db.query(Product).filter(Product.is_active == True).all()
    print(f"  Found {len(products)} active products in DB")

    if not products:
        print("\n  No products found! Run 'python -m app.utils.seed_products' first.")
        db.close()
        return

    # ── Step 5: Create orders for each user ──
    print("\nCreating orders...")
    all_orders = []
    orders_created = 0

    for user in users:
        user_addrs = [a for a in all_addresses if a.user_id == user.id]
        shipping_addr = next((a for a in user_addrs if a.type == "shipping"), user_addrs[0])
        billing_addr = next((a for a in user_addrs if a.type == "billing"), None)

        if not shipping_addr:
            continue

        num_orders = random.choices([2, 3, 4, 5], weights=[3, 4, 2, 1])[0]

        for _ in range(num_orders):
            status = _pick_status()
            num_items = random.randint(1, 3)
            selected = random.sample(products, min(num_items, len(products)))

            order_date = datetime.datetime.now() - timedelta(
                days=random.randint(1, 180),
                hours=random.randint(0, 23),
            )

            total = 0.0
            items_data = []
            for p in selected:
                qty = random.randint(1, 3)
                unit_price = float(p.selling_price or p.price or 0)
                unit_cost = float(p.buying_price or unit_price * random.uniform(0.4, 0.7))
                total += unit_price * qty
                items_data.append({
                    "product_id": p.id,
                    "quantity": qty,
                    "unit_price": round(unit_price, 2),
                    "unit_cost": round(unit_cost, 2),
                })

            shipping_cost = random.choice([0, 0, 40, 49, 79])
            total += shipping_cost
            tax = round(total * 0.05, 2) if random.random() < 0.5 else 0
            discount = round(total * random.uniform(0, 0.15), 2) if random.random() < 0.3 else 0
            net_total = round(total + tax - discount, 2)

            order = Order(
                user_id=user.id,
                shipping_address_id=shipping_addr.id,
                billing_address_id=billing_addr.id if billing_addr else None,
                order_number=generate_order_number(),
                total_amount=net_total,
                status=status,
                order_date=order_date,
                tx_ref=generate_trx_ref(),
                contact_name=f"{user.first_name} {user.last_name}",
                contact_phone=user.phone,
                contact_email=user.email,
                payment_mode=random.choice(["cod", "stripe", "paypal", "bank_transfer"]),
                shipping_cost=shipping_cost,
                tax=tax,
                discount=discount,
            )
            order.payment_status = "pending"

            if status == "delivered":
                order.payment_status = "success"
                order.accepted_at = order_date + timedelta(hours=random.randint(1, 12))
                order.packed_at = order.accepted_at + timedelta(hours=random.randint(2, 24))
                order.on_delivery_at = order.packed_at + timedelta(hours=random.randint(2, 12))
                order.delivered_at = order.on_delivery_at + timedelta(hours=random.randint(1, 72))

            elif status == "rejected":
                order.payment_status = "failed"
                order.rejected_at = order_date + timedelta(hours=random.randint(1, 24))
                order.reject_reason = random.choice([
                    "Out of stock", "Payment declined", "Invalid address",
                    "Fraud detected", "Duplicate order detected",
                ])

            elif status == "cancelled":
                order.payment_status = "failed"
                order.cancelled_by = random.choice(["customer", "admin"])
                order.cancel_reason = random.choice([
                    "Changed mind", "Found better price elsewhere",
                    "Ordered by mistake", "Delivery too slow",
                    "Product no longer needed",
                ])

            elif status == "refund_requested":
                order.payment_status = "success"
                order.accepted_at = order_date + timedelta(hours=random.randint(1, 12))
                order.packed_at = order.accepted_at + timedelta(hours=random.randint(2, 24))
                order.on_delivery_at = order.packed_at + timedelta(hours=random.randint(2, 12))
                order.delivered_at = order.on_delivery_at + timedelta(hours=random.randint(1, 72))
                order.refund_requested_at = order.delivered_at + timedelta(days=random.randint(1, 7))
                order.refund_reason = random.choice([
                    "Product is defective", "Wrong item delivered",
                    "Size does not match", "Quality not as expected",
                    "Item damaged during shipping",
                ])

            elif status == "refund_successful":
                order.payment_status = "success"
                order.accepted_at = order_date + timedelta(hours=random.randint(1, 12))
                order.packed_at = order.accepted_at + timedelta(hours=random.randint(2, 24))
                order.on_delivery_at = order.packed_at + timedelta(hours=random.randint(2, 12))
                order.delivered_at = order.on_delivery_at + timedelta(hours=random.randint(1, 72))
                order.refund_requested_at = order.delivered_at + timedelta(days=random.randint(1, 7))
                order.refund_out_for_pickup_at = order.refund_requested_at + timedelta(days=1)
                order.item_retrieved_from_customer_at = order.refund_out_for_pickup_at + timedelta(days=1)
                order.item_retrieved_by_admin_at = order.item_retrieved_from_customer_at + timedelta(days=2)
                order.refund_on_the_way_at = order.item_retrieved_by_admin_at + timedelta(days=1)
                order.refund_successful_at = order.refund_on_the_way_at + timedelta(days=random.randint(3, 7))
                order.refund_reason = random.choice([
                    "Product is defective", "Wrong item delivered",
                    "Size does not match", "Quality not as expected",
                    "Item damaged during shipping",
                ])

            elif status == "pending":
                order.payment_status = random.choice(["pending", "success"])

            elif status == "accepted":
                order.payment_status = "success"
                order.accepted_at = order_date + timedelta(hours=random.randint(1, 12))

            elif status == "packed":
                order.payment_status = "success"
                order.accepted_at = order_date + timedelta(hours=random.randint(1, 12))
                order.packed_at = order.accepted_at + timedelta(hours=random.randint(2, 24))

            elif status == "on_delivery":
                order.payment_status = "success"
                order.accepted_at = order_date + timedelta(hours=random.randint(1, 12))
                order.packed_at = order.accepted_at + timedelta(hours=random.randint(2, 24))
                order.on_delivery_at = order.packed_at + timedelta(hours=random.randint(2, 12))

            db.add(order)
            db.flush()
            all_orders.append(order)

            for item_data in items_data:
                oi = OrderItem(
                    order_id=order.id,
                    product_id=item_data["product_id"],
                    quantity=item_data["quantity"],
                    unit_price=item_data["unit_price"],
                    unit_cost=item_data["unit_cost"],
                )
                db.add(oi)

            pay_status = "completed" if order.payment_status == "success" else "pending"
            payment = Payment(
                order_id=order.id,
                payment_method=random.choice(["credit_card", "paypal", "bank_transfer", "stripe"]),
                amount=net_total,
                status=pay_status,
                transaction_id=generate_trx_ref(),
                paid_at=order_date if pay_status == "completed" else None,
            )
            db.add(payment)

            orders_created += 1

        db.commit()

    print(f"  Created {orders_created} orders")

    # ── Step 6: Create reviews for delivered/refunded orders ──
    print("\nCreating reviews...")
    reviewable_orders = [o for o in all_orders if o.status in (
        "delivered", "refund_requested", "refund_successful"
    )]
    reviews_created = 0

    for order in reviewable_orders:
        if random.random() > 0.7:
            continue

        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        delivered_at = (order.delivered_at or
                        order.refund_requested_at or
                        order.order_date + timedelta(days=random.randint(1, 14)))

        for item in items:
            if random.random() > 0.6:
                continue

            rating = random.choices([5, 4, 3, 2, 1], weights=[40, 30, 15, 10, 5])[0]
            comment = random.choice(REVIEW_COMMENTS[rating])
            review_date = delivered_at + timedelta(days=random.randint(1, 14))

            review = Review(
                user_id=order.user_id,
                product_id=item.product_id,
                rating=rating,
                comment=comment,
                is_approved=True,
                created_at=review_date,
            )

            if random.random() < 0.3:
                review.reply = random.choice(ADMIN_REPLIES)
                review.replied_at = review_date + timedelta(hours=random.randint(1, 48))

            db.add(review)
            reviews_created += 1

        db.commit()

    print(f"  Created {reviews_created} reviews")

    # ── Step 7: Create wishlist items ──
    print("\nCreating wishlist items...")
    wishlist_count = 0
    for user in users:
        num = random.randint(2, 5)
        wish_products = random.sample(products, min(num, len(products)))
        for p in wish_products:
            exists = db.query(Wishlist).filter(
                Wishlist.user_id == user.id,
                Wishlist.product_id == p.id,
            ).first()
            if not exists:
                db.add(Wishlist(user_id=user.id, product_id=p.id))
                wishlist_count += 1
        db.commit()
    print(f"  Created {wishlist_count} wishlist items")

    # ── Step 8: Create cart items for some users ──
    print("\nCreating cart items...")
    cart_count = 0
    for user in users:
        if random.random() < 0.4:
            continue

        cart = db.query(Cart).filter(Cart.user_id == user.id).first()
        if not cart:
            cart = Cart(user_id=user.id)
            db.add(cart)
            db.flush()

        num = random.randint(1, 3)
        cart_products = random.sample(products, min(num, len(products)))
        for p in cart_products:
            exists = db.query(CartItem).filter(
                CartItem.cart_id == cart.id,
                CartItem.product_id == p.id,
            ).first()
            if not exists:
                db.add(CartItem(cart_id=cart.id, product_id=p.id, quantity=random.randint(1, 2)))
                cart_count += 1
        db.commit()
    print(f"  Created {cart_count} cart items")

    # ── Summary ──
    db.close()
    print("\n" + "=" * 50)
    print("Seed complete! Summary:")
    print(f"  Users:         {len(users)}")
    print(f"  Addresses:     {len(all_addresses)}")
    print(f"  Orders:        {orders_created}")
    print(f"  Reviews:       {reviews_created}")
    print(f"  Wishlist:      {wishlist_count}")
    print(f"  Cart items:    {cart_count}")
    print("=" * 50)


if __name__ == "__main__":
    seed()
