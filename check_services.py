from api.models import Service
for s in Service.objects.all():
    print(f'Service: {s.title}, Category: {s.category.name if s.category else "NONE"}')
