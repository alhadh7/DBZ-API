# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .models import (
    User, Restaurant, Category, Product, 
    Cart, CartItem, Order, OrderItem
)
from .serializers import (
    UserSignupSerializer, UserLoginSerializer, RestaurantSerializer,
    CategorySerializer, ProductSerializer, CartSerializer, 
    CartItemSerializer, OrderSerializer
)
import json

from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from django.views.decorators.csrf import csrf_exempt

# Update user_signup view
@api_view(['POST'])
@permission_classes([AllowAny])
def user_signup(request):
    serializer = UserSignupSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        # Create a cart for the user
        Cart.objects.create(user=user)
        # Create token for API auth
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            "message": "User registered successfully",
            "token": token.key,
            "user_id": user.id,
            "email": user.email,
            "delivery_boy" : user.is_delivery_boy
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Update user_login view
@api_view(['POST'])
@permission_classes([AllowAny])
def user_login(request):
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        user = authenticate(request, username=email, password=password)
        
        if user and not user.is_restaurant:
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "message": "Login successful",
                "token": token.key,
                "user_id": user.id,
                "email": user.email,
                "username": user.username,
                "delivery_boy" : user.is_delivery_boy

            })
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_logout(request):
    # Delete the token to logout
    request.user.auth_token.delete()
    return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)
@api_view(['GET'])
@permission_classes([AllowAny])
def product_list(request):
    category_id = request.query_params.get('category', None)
    search_query = request.query_params.get('search', None)
    
    products = Product.objects.all()
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def restaurant_list(request):
    restaurant = Restaurant.objects.all()

    serializer = RestaurantSerializer(restaurant, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def restaurant_products(request, restaurant_id):
    products = Product.objects.filter(restaurant_id=restaurant_id, is_available=True)
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def category_list(request):
    categories = Category.objects.all()
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_cart(request):
    try:
        cart = Cart.objects.get(user=request.user)
    except Cart.DoesNotExist:
        cart = Cart.objects.create(user=request.user)
    
    serializer = CartSerializer(cart)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    product_id = request.data.get('product_id')
    quantity = int(request.data.get('quantity', 1))
    
    try:
        product = Product.objects.get(id=product_id, is_available=True)
    except Product.DoesNotExist:
        return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
    
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # Check if the item already exists in the cart
    cart_item, item_created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )
    
    if not item_created:
        cart_item.quantity += quantity
        cart_item.save()
    
    serializer = CartSerializer(cart)
    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_cart_item(request, item_id):
    try:
        cart_item = CartItem.objects.get(id=item_id, cart__user=request.user)
    except CartItem.DoesNotExist:
        return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)
    
    quantity = request.data.get('quantity', 1)
    if int(quantity) <= 0:
        cart_item.delete()
    else:
        cart_item.quantity = quantity
        cart_item.save()
    
    cart = Cart.objects.get(user=request.user)
    serializer = CartSerializer(cart)
    return Response(serializer.data)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_from_cart(request, item_id):
    try:
        cart_item = CartItem.objects.get(id=item_id, cart__user=request.user)
    except CartItem.DoesNotExist:
        return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)
    
    cart_item.delete()
    
    cart = Cart.objects.get(user=request.user)
    serializer = CartSerializer(cart)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def checkout(request):
    try:
        cart = Cart.objects.get(user=request.user)
    except Cart.DoesNotExist:
        return Response({"error": "Cart not found"}, status=status.HTTP_404_NOT_FOUND)
    
    if not cart.items.exists():
        return Response({"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Group items by restaurant
    restaurant_items = {}
    for item in cart.items.all():
        restaurant_id = item.product.restaurant.id
        if restaurant_id not in restaurant_items:
            restaurant_items[restaurant_id] = []
        restaurant_items[restaurant_id].append(item)
    
    # Create an order for each restaurant
    orders = []
    for restaurant_id, items in restaurant_items.items():
        restaurant = Restaurant.objects.get(id=restaurant_id)
        
        # Calculate total amount for this restaurant
        total_amount = sum(item.product.price * item.quantity for item in items)

                # Get latitude and longitude from the request data
        latitude = request.data.get('latitude', None)
        longitude = request.data.get('longitude', None)

        order = Order.objects.create(
            user=request.user,
            restaurant=restaurant,
            address=request.data.get('address', ''),
            phone=request.data.get('phone', ''),
            total_amount=total_amount,
            latitude=latitude,  
            longitude=longitude, 
        )
        
        # Create order items
        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
        
        orders.append(order)
    
    # Clear the cart
    cart.items.all().delete()
    
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_detail(request, id):
    try:
        order = Order.objects.get(id=id, user=request.user)
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = OrderSerializer(order)
    return Response(serializer.data)

# Restaurant Views (Django Template Views)
def restaurant_login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        
        if user and user.is_restaurant:
            login(request, user)
            return redirect('restaurant_dashboard')
        error_message = "Invalid credentials or not a restaurant account"
        return render(request, 'restaurant_login.html', {'error': error_message})
    
    return render(request, 'restaurant_login.html')

def restaurant_signup_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        restaurant_name = request.POST.get('restaurant_name')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        
        if User.objects.filter(email=email).exists():
            error_message = "Email already exists"
            return render(request, 'restaurant_signup.html', {'error': error_message})
        
        # Create user with restaurant flag
        user = User.objects.create_user(
            email=email,
            username=username,
            password=password,
            is_restaurant=True
        )
        
        # Create restaurant profile
        Restaurant.objects.create(
            user=user,
            name=restaurant_name,
            address=address,
            phone=phone
        )
        
        login(request, user)
        return redirect('restaurant_dashboard')
    
    return render(request, 'restaurant_signup.html')

@login_required
def restaurant_logout_view(request):
    logout(request)
    return redirect('restaurant_login')

@login_required
def restaurant_dashboard(request):
    if not hasattr(request.user, 'restaurant'):
        logout(request)
        return redirect('restaurant_login')
    
    restaurant = request.user.restaurant
    products = Product.objects.filter(restaurant=restaurant)
    orders = Order.objects.filter(restaurant=restaurant).order_by('-created_at')
    pending_orders = orders.filter(status='pending')

    context = {
        'restaurant': restaurant,
        'products': products,
        'pending_orders_count': pending_orders.count(),

        'orders': orders
    }
    
    return render(request, 'restaurant_dashboard.html', context)

@login_required
def add_product(request):
    if not hasattr(request.user, 'restaurant'):
        return redirect('restaurant_login')
    
    categories = Category.objects.all()
    
    if request.method == 'POST':
        restaurant = request.user.restaurant
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        category_id = request.POST.get('category')
        
        category = get_object_or_404(Category, id=category_id)
        
        product = Product.objects.create(
            restaurant=restaurant,
            name=name,
            description=description,
            price=price,
            category=category
        )
        
        if 'image' in request.FILES:
            product.image = request.FILES['image']
            product.save()
        
        return redirect('restaurant_dashboard')
    
    return render(request, 'add_product.html', {'categories': categories})

@login_required
def restaurant_orders(request):
    if not hasattr(request.user, 'restaurant'):
        return redirect('restaurant_login')
    
    restaurant = request.user.restaurant
    orders = Order.objects.filter(restaurant=restaurant).order_by('-created_at')
    
    return render(request, 'restaurant_orders.html', {'orders': orders})

@login_required
def update_order_status(request, order_id):
    if not hasattr(request.user, 'restaurant'):
        return redirect('restaurant_login')
    
    if request.method == 'POST':
        restaurant = request.user.restaurant
        order = get_object_or_404(Order, order_id=order_id, restaurant=restaurant)
        status = request.POST.get('status')
        
        if status in dict(Order.STATUS_CHOICES).keys():
            order.status = status
            order.save()
    
    return redirect('restaurant_orders')


@login_required
def edit_product(request, product_id):
    if not hasattr(request.user, 'restaurant'):
        return redirect('restaurant_login')
    
    restaurant = request.user.restaurant
    product = get_object_or_404(Product, id=product_id, restaurant=restaurant)
    categories = Category.objects.all()
    
    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        product.category_id = request.POST.get('category')
        product.is_available = 'is_available' in request.POST
        
        if 'image' in request.FILES:
            product.image = request.FILES['image']
        
        product.save()
        return redirect('restaurant_dashboard')
    
    context = {
        'product': product,
        'categories': categories
    }
    
    return render(request, 'edit_product.html', context)

@login_required
def delete_product(request, product_id):
    if not hasattr(request.user, 'restaurant'):
        return redirect('restaurant_login')
    
    restaurant = request.user.restaurant
    product = get_object_or_404(Product, id=product_id, restaurant=restaurant)
    
    if request.method == 'POST':
        product.delete()
        return redirect('restaurant_dashboard')
    
    context = {
        'product': product
    }
    
    return render(request, 'delete_product.html', context)

@login_required
def restaurant_profile(request):
    if not hasattr(request.user, 'restaurant'):
        return redirect('restaurant_login')
    
    restaurant = request.user.restaurant
    
    if request.method == 'POST':
        restaurant.name = request.POST.get('name')
        restaurant.address = request.POST.get('address')
        restaurant.phone = request.POST.get('phone')
        restaurant.save()
        return redirect('restaurant_dashboard')
    
    return render(request, 'restaurant_profile.html', {'restaurant': restaurant})


from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from .models import Order

def order_details(request, order_id):
    # Fetch the order using its order_id
    order = get_object_or_404(Order, order_id=order_id)
    
    # Fetch related order items
    order_items = order.items.all()
    
    # You can return the order and its items in a simple JSON response (or HTML if you prefer)
    order_details = {
        'order_id': order.order_id,
        'status': order.status,
        'total_amount': order.total_amount,
        'address': order.address,
        'phone': order.phone,
        'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'order_items': [
            {
                'product_name': item.product.name,
                'quantity': item.quantity,
                'price': item.price,
                'total_price': item.total_price,
            }
            for item in order_items
        ]
    }
    
    return JsonResponse(order_details)


from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from .models import Order

@csrf_exempt
def update_order_status(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, order_id=order_id)
        new_status = request.POST.get('status')

        # Ensure the status is valid and the current status is not the same as the selected status
        if new_status in dict(Order.STATUS_CHOICES).keys() and new_status != order.status:
            order.status = new_status
            order.save()

            # Add a success message
            messages.success(request, f'Order {order.order_id} status updated to {order.get_status_display()}.')

        else:
            # Add an error message if the status is invalid or unchanged
            messages.error(request, 'Invalid status or status is already set to this value.')

    return redirect('restaurant_orders')  # Redirect to the dashboard or another page


from rest_framework.permissions import BasePermission

class IsDeliveryBoy(BasePermission):
    def has_permission(self, request, view):
        # Only allow access if the user is a delivery boy
        return request.user.is_authenticated and request.user.is_delivery_boy


from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Order

from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsDeliveryBoy])
def update_order_status_d(request, id):
    try:
        order = Order.objects.get(id=id)
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        
    # Check if the user is the assigned delivery boy for the order
    if order.delivery_boy != request.user:
        return Response({"error": "You are not authorized to update this order"}, status=status.HTTP_403_FORBIDDEN)
        
    new_status = request.data.get('status')
        
    if new_status not in dict(Order.STATUS_CHOICES).keys():
        return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)
        
    # Update the order status
    order.status = new_status
    order.save()
        
    return Response({
        "message": "Order status updated successfully",
        "order_id": str(order.order_id),  # Convert UUID to string
        "status": order.status
    }, status=status.HTTP_200_OK)



from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from .models import Order
from rest_framework.permissions import IsAuthenticated

# Check if the user is a delivery boy
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsDeliveryBoy])  # Ensure the user is authenticated and a delivery boy
def get_orders_assigned_to_delivery_boy(request):
    # Get orders assigned to the logged-in delivery boy
    orders = Order.objects.filter(delivery_boy=request.user)  # Filter orders by delivery_boy

    # If no orders found, return a message saying no orders are assigned
    if not orders.exists():
        return Response({"message": "No orders assigned to you."}, status=status.HTTP_404_NOT_FOUND)
    
    # Prepare the order data to return in the response
    order_data = []
    for order in orders:
        order_data.append({
            "id": order.id,
            "order_id": str(order.order_id),  # Convert UUID to string
            "address": order.address,
            "status": order.status,
            "phone": order.phone,
            "latitude": order.latitude,
            "longitude": order.longitude,
        })

    return Response({
        "message": "Orders retrieved successfully.",
        "orders": order_data
    }, status=status.HTTP_200_OK)
