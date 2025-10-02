from django.contrib import admin
from .models import *

# Register your models here.
class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'order_date', 'status']
    inlines = [PurchaseItemInline]

admin.site.register(Material)
admin.site.register(Category)
admin.site.register(Unit)


admin.site.register(Vendor)
admin.site.register(PurchaseItem)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(OrderItem)