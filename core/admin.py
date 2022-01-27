from re import search
from ssl import ALERT_DESCRIPTION_BAD_CERTIFICATE_STATUS_RESPONSE
from django.contrib import admin
from .models import Item, OrderItem, Order, Payment, Coupon, Refund, Address


# Register your models here.
def make_refund_accepted(modeladmin, request, queryset):
    queryset.update(refund_requested=False, refund_granted=True)

make_refund_accepted.short_description = 'Update orders to refund granted'    


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'ordered',
        'being_delivered',
        'received',
        'refund_requested',
        'refund_granted',
        'address',
        'payment',
        'coupon',
    ]

    list_display_links = [
        'user',
        'address',
        'payment',
        'coupon',
    ]

    list_filter = [
        'ordered',
        'being_delivered',
        'received',
        'refund_requested',
        'refund_granted',
    ]

    search_fields = [
        'user__username',
        'ref_code',
    ]

    actions = [make_refund_accepted]

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'street_address',
        'apartment_address',
        'country',
        'zip',
        'default'
    
    ]  

    list_filter = [
        'user',
        'country',
    ] 

    search_fields = [
        'user',
        'street_address',
        'apartment_address',
        'zip',
    ]       

# Register your models here.
admin.site.register(Item)
admin.site.register(OrderItem)
admin.site.register(Payment)
admin.site.register(Coupon)
admin.site.register(Refund)


