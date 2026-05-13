from api.models import Agent
try:
    a = Agent.objects.get(name__icontains="faiyaz")
    print(f"Agent: {a.name}, Email: {a.email}")
except Exception as e:
    print(e)
