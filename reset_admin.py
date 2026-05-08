import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import User

admin_email = "admin@bm.com"
new_password = "admin123"

try:
    user = User.objects.get(email=admin_email)
    user.set_password(new_password)
    user.save()
    print(f"Successfully reset password for {admin_email} to: {new_password}")
except User.DoesNotExist:
    print(f"User {admin_email} not found. Creating a new superuser...")
    User.objects.create_superuser(
        username="admin",
        email=admin_email,
        password=new_password
    )
    print(f"Successfully created superuser {admin_email} with password: {new_password}")
except Exception as e:
    print(f"Error: {e}")
