import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import Service, Category

# 1. Create Categories
cats_data = [
    {"name": "Laundry", "icon": "Droplets"},
    {"name": "Cleaning", "icon": "Shield"},
    {"name": "Electric Service", "icon": "Zap"},
    {"name": "Tech Support", "icon": "Smartphone"},
    {"name": "Daily Needs", "icon": "Grid"},
]

cats = {}
for cd in cats_data:
    cat, _ = Category.objects.get_or_create(name=cd['name'], defaults={'icon': cd['icon']})
    cats[cd['name']] = cat
    print(f"Category: {cat.name}")

# 2. Create Services
services_data = [
    {
        "title": "Express Laundry",
        "category": "Laundry",
        "description": "Wash, fold, and iron. Delivered fresh to your doorstep in 24 hours.",
        "price": 99.00,
        "image_url": "https://images.unsplash.com/photo-1545173168-9f1947eebb7f?w=600&h=400&fit=crop"
    },
    {
        "title": "Deep Room Cleaning",
        "category": "Cleaning",
        "description": "Professional cleaning for your hostel or apartment. Spotless results guaranteed.",
        "price": 499.00,
        "image_url": "https://images.unsplash.com/photo-1581578731548-c64695ce6958?w=600&h=400&fit=crop"
    },
    {
        "title": "Electric Repair",
        "category": "Electric Service",
        "description": "Fixing fans, lights, switches and wiring. Rated 5-stars by users.",
        "price": 149.00,
        "image_url": "https://images.unsplash.com/photo-1621905251189-08b45d6a269e?w=600&h=400&fit=crop"
    },
    {
        "title": "Laptop Optimization",
        "category": "Tech Support",
        "description": "Software cleanup, thermal pasting, and performance tuning for students.",
        "price": 299.00,
        "image_url": "https://images.unsplash.com/photo-1593642632823-8f785ba67e45?w=600&h=400&fit=crop"
    },
    {
        "title": "Grocery Run",
        "category": "Daily Needs",
        "description": "Quick delivery of snacks, stationery, and essentials within 30 minutes.",
        "price": 49.00,
        "image_url": "https://images.unsplash.com/photo-1542838132-92c53300491e?w=600&h=400&fit=crop"
    }
]

for s in services_data:
    Service.objects.create(
        title=s['title'],
        category=cats[s['category']],
        description=s['description'],
        price=s['price'],
        image_url=s['image_url']
    )
    print(f"Service: {s['title']}")

print("New dynamic seeding complete!")
