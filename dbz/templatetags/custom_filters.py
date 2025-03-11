from django import template
from ..models import Order
from django.db.models.query import QuerySet

register = template.Library()

@register.filter
def filter_by_status(orders, status):
    return orders.filter(status=status)

