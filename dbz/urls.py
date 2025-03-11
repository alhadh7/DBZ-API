# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # User API endpoints
    path('api/users/signup/', views.user_signup, name='user_signup'),
    path('api/users/login/', views.user_login, name='user_login'),
    path('api/users/logout/', views.user_logout, name='user_logout'),

    path('api/products/', views.product_list, name='product_list'),
    path('api/restaurant/', views.restaurant_list, name='restaurant_list'),

    path('api/restaurants/<int:restaurant_id>/products/', views.restaurant_products, name='restaurant_products'),
    path('api/categories/', views.category_list, name='category_list'),
    path('api/cart/', views.get_cart, name='get_cart'),
    path('api/cart/add/', views.add_to_cart, name='add_to_cart'),
    path('api/cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('api/cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('api/checkout/', views.checkout, name='checkout'),
    path('api/orders/', views.order_list, name='order_list'),
    path('api/orders/<int:id>/', views.order_detail, name='order_detail'),
    
    # Restaurant web interface
    path('restaurant/login/', views.restaurant_login_view, name='restaurant_login'),
    path('restaurant/signup/', views.restaurant_signup_view, name='restaurant_signup'),
    path('restaurant/logout/', views.restaurant_logout_view, name='restaurant_logout'),
    path('restaurant/dashboard/', views.restaurant_dashboard, name='restaurant_dashboard'),
    path('restaurant/products/add/', views.add_product, name='add_product'),
    path('restaurant/products/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('restaurant/products/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    path('restaurant/profile/', views.restaurant_profile, name='restaurant_profile'),    
    path('restaurant/orders/', views.restaurant_orders, name='restaurant_orders'),
    path('restaurant/orders/<uuid:order_id>/update/', views.update_order_status, name='update_order_status'),
    path('orders/<uuid:order_id>/details/', views.order_details, name='order-details'),
    path('orders/<uuid:order_id>/update-status/', views.update_order_status, name='update-order-status'),

    path('api/orders/assigned/', views.get_orders_assigned_to_delivery_boy, name='get_orders_assigned_to_delivery_boy'),
    path('api/orders/<int:id>/update_status_d/', views.update_order_status_d, name='update_order_status_d'),
]