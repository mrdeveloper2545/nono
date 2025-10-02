from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Order

User = get_user_model()

@receiver(pre_save, sender=Order)
def store_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            previous = Order.objects.get(pk=instance.pk)
            instance._previous_status = previous.status
        except Order.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None

@receiver(post_save, sender=Order)
def send_order_status_email(sender, instance, created, **kwargs):
    try:
        old_status = getattr(instance, '_previous_status', None)
        subject = None

        if created:
            # Send "Order Confirmation" email only once on creation
            subject = 'Order Confirmation'
        else:
            # Send emails only if status changed after creation
            if instance.status != old_status:
                if instance.status == 'approved':
                    subject = 'Order Approved'
                elif instance.status == 'cancelled':
                    subject = 'Order Cancelled'

        if subject is None:
            return  # No email to send

        # Prepare order items info
        items = instance.items.all()
        product_lines = []
        for item in items:
            product_name = item.product.name
            qty = item.quantity
            price = item.product.wholesale_price if instance.order_type == 'wholesale' else item.product.retail_price
            subtotal = price * qty
            product_lines.append(f"- {product_name} x {qty} @ ${price:.2f} = ${subtotal:.2f}")

        product_details = "\n".join(product_lines)
        total_price = instance.total_price

        # Email message body
        message = f"""
Dear {instance.user.username},

Your order (ID: {instance.order_id}) has been updated to: {instance.status.upper()}.

Order Summary:
{product_details if product_details else 'No items in this order.'}

Total: ${total_price:.2f}
Date: {instance.order_date.strftime('%Y-%m-%d')}
Status: {instance.status}

Thank you for your purchase!

Best regards,  
NUSUBEI GROUP
        """

        # Send email to customer
        send_mail(
            subject=subject,
            message=message.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.user.email],
            fail_silently=False,
        )

        # Send email to all superusers
        superuser_emails = User.objects.filter(is_superuser=True).values_list('email', flat=True)
        superuser_emails = [email for email in superuser_emails if email]

        if superuser_emails:
            send_mail(
                subject=subject,
                message=message.strip(),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=superuser_emails,
                fail_silently=False,
            )

    except Exception as e:
        print(f"[Order Email Error] {e}")
