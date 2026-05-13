from api.models import Service, Agent, Category
services = Service.objects.all()
print('--- Services ---')
for s in services:
    print(f'Service: {s.title}, Category: {s.category.name if s.category else "None"}')

categories = Category.objects.all()
print('\n--- Categories & Agents ---')
for c in categories:
    print(f'Category: {c.name}, Agents: {c.agents.count()}')
