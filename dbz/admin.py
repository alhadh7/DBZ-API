# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Restaurant, Category, Product, 
    Cart, CartItem, Order, OrderItem
)

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['email', 'username', 'is_restaurant', 'is_delivery_boy', 'is_staff']  # Add is_delivery_boy to list_display
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('is_restaurant', 'is_delivery_boy')}),  # Add is_delivery_boy to fieldsets
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('email', 'is_restaurant', 'is_delivery_boy')}),  # Add is_delivery_boy to add_fieldsets
    )

class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'phone']
    search_fields = ['name', 'user__email']

class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'restaurant', 'price', 'category', 'is_available']
    list_filter = ['is_available', 'category', 'restaurant']
    search_fields = ['name', 'description', 'restaurant__name']

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'user', 'restaurant', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order_id', 'user__email', 'restaurant__name']
    inlines = [OrderItemInline]

admin.site.register(User, CustomUserAdmin)
admin.site.register(Restaurant, RestaurantAdmin)
admin.site.register(Category)
admin.site.register(Product, ProductAdmin)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)