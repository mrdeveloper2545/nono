from django.db import models
from django.contrib.auth.models import  User
from datetime import date, timedelta
from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal, DivisionByZero, InvalidOperation
from django.utils.timezone import now
from django.db.models import Sum


# Create your models here.

class Unit(models.Model):
    name=models.CharField(max_length=50)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=200)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'categories'
    def __str__(self):
        return self.name

class Material(models.Model):
    name = models.CharField(max_length=150)
    category = models.ForeignKey(Category, on_delete=models.CASCADE,)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE,)
    quantity = models.PositiveBigIntegerField(default=0)
    
    
    def __str__(self):
        return self.name

class Vendor (models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=50)
    

    def __str__(self):
        return self.name
    
    class Meta:
        permissions =[
            ('bulk_update_vendor', 'can bulk update vendor')
            ]
    
class PurchaseOrder(models.Model):
    order_number = models.CharField(max_length=200, unique=True)
    order_date = models.DateField()
    expected_delivery_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=100, default='pending')
    received_date = models.DateTimeField(blank=True, null=True)
    cancelled_date = models.DateTimeField(blank=True, null=True)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    

    _original_status = None  # To track changes to status

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_status = self.status  # capture initial status

    def save(self, *args, **kwargs):
        # Generate order number if not set
        if not self.order_number:
            current_year = now().year
            last_order = (
                PurchaseOrder.objects.select_for_update()
                .filter(order_number__startswith=f"PO-{current_year}")
                .order_by('-id')
                .first()
            )

            if last_order and last_order.order_number:
                try:
                    last_number = int(last_order.order_number.split("-")[-1])
                except (IndexError, ValueError):
                    last_number = 0
            else:
                last_number = 0

            new_number = last_number + 1
            self.order_number = f"PO-{current_year}-{new_number:04d}"

        # Check if this is a status change to "approved"
        is_being_approved = self._original_status != 'approved' and self.status == 'approved'

        super().save(*args, **kwargs)  # save the PO

        # If status has changed to approved, update material quantities
        if is_being_approved:
            for item in self.items.all():  # .items from related_name
                material = item.material
                material.quantity += item.quantity
                material.save()

        self._original_status = self.status 


    def __str__(self):
        return f" #{self.order_number}"
        
    def clean(self):
        if self.expected_delivery_date and self.expected_delivery_date < self.order_date:
            raise ValidationError("Expected delivery date cannot be before the order date.")
        
            
    def update_total_cost(self):
        total = sum(item.total_price for item in self.items.all())
        self.total_cost = total
        self.save()



    class Meta:
        permissions=[
            ('cancel_purchase_order', 'Can cancel purchase order'),
            ('approve_purchase_order', 'Can approve purchase order'),
            ('generate_invoice', 'Can generate invoice'),
            ('generate_report', 'Can generate report')
        ]


class PurchaseItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='items')
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        # Ensure price is Decimal
        if not isinstance(self.price, Decimal):
            try:
                self.price = Decimal(str(self.price))
            except InvalidOperation:
                self.price = Decimal('0.00')

        # Calculate unit price
        if self.quantity > 0:
            self.unit_price = self.price / self.quantity
        else:
            self.unit_price = Decimal('0.00')

        super().save(*args, **kwargs)

        # Update the parent purchase order's total cost
        self.purchase_order.update_total_cost()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.purchase_order.update_total_cost()

    @property
    def total_price(self):
        return self.price

    def __str__(self):
        return f"{self.material.name} (x{self.quantity})"


class Product(models.Model):
    product = models.OneToOneField(Material, on_delete=models.CASCADE, related_name='product',)
    retail_price = models.DecimalField(max_digits=10, decimal_places=2)
    wholesale_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    description = models.TextField(blank=True,null=True)
    threshold_quantity = models.PositiveIntegerField()

    def __str__(self):
        return self.product.name

    def save(self, *args, **kwargs):
        if self.pk:
            # Editing existing product
            old = Product.objects.get(pk=self.pk)
            quantity_diff = self.quantity - old.quantity
        else:
            # New product
            quantity_diff = self.quantity

        material = self.product
        if material.quantity - quantity_diff < 0:
            raise ValueError(f"Not enough stock of material '{material.name}'.")

        material.quantity -= quantity_diff
        material.save()

        super().save(*args, **kwargs)



class Order(models.Model):
    ORDER_TYPE_CHOICES = [
        ('wholesale', 'Wholesale'),
        ('retail', 'Retail'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled'),
    ]

    order_id = models.CharField(max_length=100, unique=True)
    order_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    approved_date = models.DateTimeField(blank=True, null=True)
    cancelled_date = models.DateTimeField(blank=True, null=True)
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES, default='retail')
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    
    _original_status = None  # Track original status

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_status = self.status

    def save(self, *args, **kwargs):
        # Generate order_id if not set
        if not self.order_id:
            current_year = now().year
            last_order = Order.objects.filter(order_id__startswith=f"ORD-{current_year}").order_by('-id').first()

            if last_order and last_order.order_id:
                try:
                    last_number = int(last_order.order_id.split("-")[-1])
                except (IndexError, ValueError):
                    last_number = 0
            else:
                last_number = 0

            new_number = last_number + 1
            self.order_id = f"ORD-{current_year}-{new_number:04d}"

        # Check for approval
        is_approving = self._original_status != 'approved' and self.status == 'approved'

        super().save(*args, **kwargs)  # Save order

        if is_approving:
            self.approved_date = now()
            for item in self.items.all():  # .items from related_name
                product = item.product
                if product.quantity < item.quantity:
                    raise ValueError(f"Not enough stock for product: {product.product}")
                product.quantity -= item.quantity
                product.save()

        self._original_status = self.status  # update original status

    def calculate_total(self):
        total = Decimal('0.00')
        for item in self.items.all():
            price = item.product.wholesale_price if self.order_type == 'wholesale' else item.product.retail_price
            total += price * item.quantity
        return total

    def update_total(self):
        self.total_price = self.calculate_total()
        self.save()

    def __str__(self):
        return f"Order {self.order_id} - {self.status}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='order_items')
    quantity = models.PositiveIntegerField()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.order.update_total()

    def delete(self, *args, **kwargs):
        order = self.order
        super().delete(*args, **kwargs)
        order.update_total()

    def __str__(self):
        return f"{self.quantity} x {self.product} for {self.order}"





