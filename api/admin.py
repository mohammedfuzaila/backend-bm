from django.contrib import admin
from .models import User, Service, Booking, Agent, Category

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_staff')

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'price', 'is_featured', 'has_image')
    list_filter = ('category', 'is_featured')
    search_fields = ('title', 'description')

    def has_image(self, obj):
        return bool(obj.image or obj.image_url)
    has_image.boolean = True

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'service', 'status', 'assigned_agent', 'amount', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'user__username', 'service__title', 'assigned_agent__name')

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'is_available')
    list_filter = ('is_available',)
    search_fields = ('name', 'email')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon')
