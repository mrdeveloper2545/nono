from django.shortcuts import render, redirect, get_list_or_404, get_object_or_404
from .models import Unit,Material,Category,Vendor,PurchaseItem,PurchaseOrder,Product,Order,OrderItem
from dashboard.models import Settings
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from datetime import datetime, timedelta
from django.contrib import messages
from django.db.models import Sum,F, ExpressionWrapper, DecimalField
from django.http import HttpResponse,HttpResponseForbidden
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from io import BytesIO
import json
from django.utils import timezone
from django.db.models.functions import TruncDate
from django.utils.dateparse import parse_date
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
from django.conf import settings
import os
from django.db import transaction
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from django.http import HttpResponse
from io import BytesIO






# Create your views here.

# UNIT MANAGEMENT VIEW
class UnitManagement(View,PermissionRequiredMixin,LoginRequiredMixin):
    template_name='unit/management.html'
    permission_required='inventory.view_unit'

    def get(self,request,*args,**kwargs):
        settings = Settings.objects.first()
        messages_data = [{"message":message.message, 'tags':message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)
        units=Unit.objects.all()
        now=datetime.now()
        context={
            'time':now,
            'year':now.year,
            'month':now.strftime('%B'),
            'day':now.strftime('%A'),
            'units':units,
            'settings':settings,
            'messages_json':messages_json,
        }
        return render(request, self.template_name,context)

    def post(self,request,*args,**kwargs):
        names = request.POST.getlist('name[]')

        if not names:
            messages.info(request, 'name are not provided')
            return redirect('unit-management')

        if Unit.objects.filter(name__in=names).exists():
            messages.info(request, 'One or more units with the given names already exists')
            return redirect('unit-management')

        units = []
        for name in names:
            unit = Unit(name=name)
            units.append(unit)

        Unit.objects.bulk_create(units)
        messages.success(request, 'units added successfully')
        return redirect('unit-management')

class UpdateDeleteUnit(View,PermissionRequiredMixin,LoginRequiredMixin):
    def get(self,request,id,*args,**kwargs):
        Unit.objects.get(id=id).delete()
        messages.success(request, 'unit deleted successfully')
        return redirect('unit-management')

    def post(self,request,id,*args,**kwargs):
        unit = Unit.objects.get(id=id)
        names=request.POST.getlist('name[]')

        for i in range(len(names)):
            name = names[i]


            existing_unit = Unit.objects.filter(name__in=names).exclude(id=unit.id).first()
            if existing_unit:
                messages.error(request, 'unit with that name already exist')
                return redirect('unit-management')


        if i == 0:
            unit.name = name
            unit.save()
        else:
            new_unit = Unit(name=name)
            new_unit.save()
            messages.success(request, 'unit updated successfully')
        return redirect('unit-management')

class BulkUpdateUnit(View, LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = ''

    def post(self, request, *args, **kwargs):
        units = get_list_or_404(Unit)


        for unit in units:
            updated_name = request.POST.get(f'name_{unit.id}')

            # check existing unit
            existing_unit = Unit.objects.filter(name=updated_name).exclude(id=unit.id).first()
            if existing_unit:
                messages.error(request, f"unit with ID {unit.id} already have the same name")

            # Update after checking complete
            unit.name = updated_name
        Unit.objects.bulk_update(units, ['name'])
        messages.success(request, 'units updated successfully')
        return redirect('unit-management')


# CATEGORY MANAGEMENT VIEW
class CategoryManagement(PermissionRequiredMixin, LoginRequiredMixin, View):
    template_name = 'category/management.html'
    permission_required = 'inventory.view_category'

    def get(self, request, *args, **kwargs):
        settings = Settings.objects.first()
        categories = Category.objects.all()
        now = datetime.now()

        # Serialize messages for the current request
        messages_data = [{'message': message.message, 'tags': message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)

        context = {
            'categories': categories,
            'time': now,
            'year': now.year,
            'month': now.strftime('%B'),
            'day': now.strftime('%A'),
            'messages_json': messages_json,
            'settings':settings
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        names = request.POST.getlist('name[]')
        if not names:
            messages.error(request, 'Names are not provided')
            return redirect('category-management')

        if Category.objects.filter(name__in=names).exists():
            messages.error(request, 'One or category with the given names already exist')
            return redirect ('category-management')

        categories = []
        for name in names:
            category = Category(name=name)
            categories.append(category)

        Category.objects.bulk_create(categories)
        messages.success(request, 'Category created successfully')
        return redirect('category-management')

class UpdateDeleteCategory(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = ""

    def post(self, request, id, *args, **kwargs):
        category = get_object_or_404(Category, id=id)

        names = request.POST.getlist('name[]')
        for i in range(len(names)):

            existing_category = Category.objects.filter(name__in=names).exclude(id=category.id).first()
            if existing_category:
                messages.error(request, 'Category with name already exist')
                return redirect('category-management')

            if i == 0:
                category.name = names[i]
                category.save()
            else:
                new_category = Category(name=names[i])
                new_category.save()
                messages.success(request, 'category updated successfully')
        return redirect('category-management')

    def get(self, request, id, *args, **kwargs):
        Category.objects.get(id=id).delete()
        messages.success(request, 'category deleted successfully')
        return redirect('category-management')

class BulkUpdateCategory(View, LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = 'inventory.change_category'

    def post(self, request, *args, **kwargs):
        categories = get_list_or_404(Category)

        for category in categories:
            updated_category = request.POST.get(f'name_{category.id}')
            existing_category = Category.objects.filter(name=updated_category).exclude(id=category.id).first()
            if existing_category:
                messages.error(request, f'category with id {category.id} already exist')
            category.name = updated_category
        Category.objects.bulk_update(categories, ['name'])
        messages.success(request, 'categories updated successfully')
        return redirect('category-management')




# MATERIAL MANAGEMENT VIEW
class MaterialManagement(LoginRequiredMixin, PermissionRequiredMixin, View):

    template_name = 'material/management.html'
    permission_required = 'inventory.view_material'

    def get(self, request, *args, **kwargs):
        settings = Settings.objects.first()
        materials = Material.objects.all()
        units = Unit.objects.all()
        categories = Category.objects.all()
        now = timezone.datetime.now()
        messages_data = [{'messages':message.message,'tags':message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)
        context={
            'materials':materials,
            'time':now,
            'messages_json':messages_json,
            'month':now.strftime('%B'),
            'day':now.strftime('%A'),
            'settings':settings,
            'units':units,
            'categories':categories,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        names = request.POST.getlist('name[]')
        categories = request.POST.getlist('category[]')
        units = request.POST.getlist('unit[]')

        # Validate that all lists are the same length
        if not (len(names) == len(categories) == len(units)):
            messages.error(request, 'All fields must have the same number of entries.')
            return redirect('material-management')

        # Check that names are provided
        if not names:
            messages.info(request, 'No materials provided.')
            return redirect('material-management')

        # Check for duplicate names
        existing_names = set(Material.objects.filter(name__in=names).values_list('name', flat=True))
        if existing_names:
            messages.info(request, f"The following materials already exist: {', '.join(existing_names)}")
            return redirect('material-management')

        materials = []
        for i in range(len(names)):
            category = get_object_or_404(Category, id=categories[i])
            unit = get_object_or_404(Unit, id=units[i])

            material = Material(
                name=names[i],
                category=category,
                unit=unit,
            )
            materials.append(material)

        # Bulk create all materials
        Material.objects.bulk_create(materials)
        messages.success(request, 'Materials added successfully.')
        return redirect('material-management')


class UpdateDeleteMaterial(View, LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = ''

    def post(self, request, id, *args, **kwargs):
        material = Material.objects.get(id=id)

        names = request.POST.getlist('name[]')

        for i in range(len(names)):


            existing_material = Material.objects.filter(name__in=names).exclude(id=material.id).first()
            if existing_material:
                continue


            if i == 0:
                material.name = names[i]
                material.save()

            else:

                new_material = Material(
                    name = names[i]
                )
                new_material.save()
                messages.success(request, 'material updated successfully')
        return redirect('material-management')



    def get(self, request, id, *args, **kwargs):
        Material.objects.get(id=id).delete()
        messages.success(request, 'material deleted successfully')
        return redirect('material-management')

class BulkUpdateMaterial(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = ''
    def post(self, request, *args, **kwargs):
        materials = get_list_or_404(Material)

        for material in materials:
            update_material = request.POST.get(f'name_{material.id}')
            material.name = update_material
        Material.objects.bulk_update(materials, ['name'])
        messages.success(request, 'Materials updated successfully')
        return redirect('material-management')



# VENDOR MANAGEMENT VIEW
class VendorManagement(View, LoginRequiredMixin, PermissionRequiredMixin):
    template_name = 'vendor/vendor.html'
    permission_required = 'inventory.view_vendor'

    def get(self, request, *args, **kwargs):
        now = timezone.datetime.now()
        messages_data = [{'messages':message.message,'tags':message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)
        vendors = Vendor.objects.all()
        settings = Settings.objects.first()
        materials = Material.objects.all()

        context = {
            'time':now,
            'year':now.year,
            'month':now.strftime('%B'),
            'day':now.strftime('%A'),
            'messages_json':messages_json,
            'vendors':vendors,
            'settings':settings,
            'materials':materials
        }
        return render(request, self.template_name,context)


    def post(self, request, *args, **kwargs):
        user = request.POST.get('user')
        names = request.POST.getlist('name[]')
        phones = request.POST.getlist('phone_number[]')

        user = request.user
        vendors = []
        for name,phone_number in zip(names,phones):
            vendors.append(Vendor(name=name,user=user,phone_number=phone_number))
        Vendor.objects.bulk_create(vendors)
        print('created')
        return redirect('vendor-management')

class BulkUpdateVendors(View, LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = ''

    def post(self, request, *args, **kwargs):
        vendors = get_list_or_404(Vendor)

        for vendor in vendors:
            vendor.name = request.POST.get(f'name_{vendor.id}')
            vendor.phone_number = request.POST.get(f'phone_number_{vendor.id}')


        Vendor.objects.bulk_update(vendors, ['name','phone_number'])
        return redirect('vendor-management')


class UpdateDeleteVendor(View, LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = ''

    def get(self, request, id, *args, **kwargs):
        Vendor.objects.get(id=id).delete()
        messages.success(request, 'vendor deleted successfully')
        return redirect('vendor-management')


    def post(self, request, id, *args, **kwargs):
        name = request.POST.get('name')
        phone_number = request.POST.get('phone_number')
        Vendor.objects.filter(id=id).update(name=name,phone_number=phone_number)
        messages.success(request, 'vendor updated successfully')
        return redirect('vendor-management')


# PURCHASEORDERMANAGEMENT

class PurchaseManagementView(PermissionRequiredMixin, LoginRequiredMixin, View):
    template_name = 'purchase/management.html'
    permission_required = 'inventory.view_purchaseorder'

    def get(self, request, *args, **kwargs):
        now = timezone.now()
        messages_data = [{'messages': message.message, 'tags': message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)

        context = {
            'time': now,
            'year': now.year,
            'month': now.strftime('%B'),
            'day': now.strftime('%A'),
            'messages_json': messages_json,
            'settings': Settings.objects.first(),
            'vendors': Vendor.objects.all(),
            'materials': Material.objects.all(),
            'po': PurchaseOrder.objects.all().order_by('-id'),
        }

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        vendor_ids = request.POST.getlist('vendor[]')
        material_ids = request.POST.getlist('material[]')
        quantities = request.POST.getlist('quantity[]')
        prices = request.POST.getlist('price[]')
        order_date_str = request.POST.get('order_date')

        if not order_date_str:
            messages.error(request, "Order date is required.")
            return redirect('purchase-management')

        if not (len(vendor_ids) == len(material_ids) == len(quantities) == len(prices)):
            messages.error(request, "Mismatch in purchase items data.")
            return redirect('purchase-management')

        try:
            order_date = datetime.strptime(order_date_str, '%Y-%m-%d').date()
            print("Parsed order_date:", order_date)
        except ValueError:
            messages.error(request, "Invalid order date format.")
            return redirect('purchase-management')

        # Bulk fetch related objects for efficiency
        materials = Material.objects.in_bulk(material_ids)
        vendors = Vendor.objects.in_bulk(vendor_ids)

        try:
            with transaction.atomic():
                po = PurchaseOrder(order_date=order_date, status='pending')
                po.save()


                created_items = 0
                for i in range(len(material_ids)):
                    try:
                        material = materials.get(int(material_ids[i]))
                        vendor = vendors.get(int(vendor_ids[i]))
                        quantity = int(quantities[i])
                        price = Decimal(prices[i])

                        if quantity <= 0 or price < 0:
                            raise ValueError("Quantity must be positive and price non-negative.")

                        if not material or not vendor:
                            raise ValueError("Invalid vendor or material reference.")

                        PurchaseItem.objects.create(
                            purchase_order=po,
                            material=material,
                            vendor=vendor,
                            quantity=quantity,
                            price=price,
                        )
                        created_items += 1
                    except (ValueError, Material.DoesNotExist, Vendor.DoesNotExist, InvalidOperation) as e:
                        messages.warning(request, f"Skipping item #{i + 1}: {e}")

                if created_items == 0:
                    po.delete()
                    print("No valid items created, purchase order deleted.")
                    messages.error(request, "No valid purchase items were created. Purchase order cancelled.")
                    return redirect('purchase-management')

                messages.success(request, f"Purchase Order {po.order_number} created with {created_items} items.")
                return redirect('purchase-management')

        except Exception as e:
            messages.error(request, f"Failed to create Purchase Order: {e}")
            return redirect('purchase-management')

class UpdateDeletePurchaseOrderView(View, LoginRequiredMixin, PermissionRequiredMixin):
    permission_required =  ''

    def post(self, request, *args, **kwargs):
        po_id = kwargs.get('pk')  # or from request.POST, depending on your URL/logic

        try:
            po = PurchaseOrder.objects.get(id=po_id)
        except PurchaseOrder.DoesNotExist:
            messages.error(request, "Purchase Order not found.")
            return redirect('purchase-management')

        # Extract data from request.POST (including items data)
        order_date_str = request.POST.get('order_date')
        vendor_ids = request.POST.getlist('vendor[]')
        material_ids = request.POST.getlist('material[]')
        quantities = request.POST.getlist('quantity[]')
        prices = request.POST.getlist('price[]')
        item_ids = request.POST.getlist('item_id[]')  # For existing items (empty string for new ones)

        # Validate order_date, parse as date, handle errors, etc.
        # Update PurchaseOrder fields
        if order_date_str:
            try:
                po.order_date = datetime.strptime(order_date_str, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, "Invalid order date format.")
                return redirect('purchase-management')

        # Wrap update in transaction
        try:
            with transaction.atomic():
                po.save()

                existing_item_ids = set(po.items.values_list('id', flat=True))
                submitted_item_ids = set()

                for i in range(len(material_ids)):
                    item_id = item_ids[i]
                    quantity = int(quantities[i])
                    price = Decimal(prices[i])
                    vendor = Vendor.objects.get(id=vendor_ids[i])
                    material = Material.objects.get(id=material_ids[i])

                    if item_id:  # Update existing item
                        submitted_item_ids.add(int(item_id))
                        item = PurchaseItem.objects.get(id=item_id, purchase_order=po)
                        item.quantity = quantity
                        item.price = price
                        item.vendor = vendor
                        item.material = material
                        item.save()
                    else:  # Create new item
                        PurchaseItem.objects.create(
                            purchase_order=po,
                            vendor=vendor,
                            material=material,
                            quantity=quantity,
                            price=price
                        )

                # Optionally, delete removed items:
                items_to_delete = existing_item_ids - submitted_item_ids
                if items_to_delete:
                    PurchaseItem.objects.filter(id__in=items_to_delete).delete()

                messages.success(request, f"Purchase Order {po.order_number} updated successfully.")
                return redirect('purchase-management')

        except Exception as e:
            messages.error(request, f"Failed to update Purchase Order: {e}")
            return redirect('purchase-management')

    def get(self, request,*args, **kwargs):
        po_id = kwargs.get('pk')
        try:
            po = PurchaseOrder.objects.get(id=po_id).delete()
            messages.success(request, 'purchase order deleted successfully')
            return redirect('purchase-management')
        except PurchaseOrder.DoesNotExist:
            messages.error(request, "Purchase Order not found.")
            return redirect('purchase-management')

class PurchaseOrderDetailView(View, PermissionRequiredMixin, LoginRequiredMixin):
    template_name = 'purchase/detail.html'
    def get(self, request, id, *args, **kwargs):
        po = PurchaseOrder.objects.get(id=id)
        now = timezone.datetime.now()
        messages_data = [{'messages':message.message,'tags':message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)
        settings = Settings.objects.first()
        context = {
            'time':now,
            'year':now.year,
            'month':now.strftime('%B'),
            'day':now.strftime('%A'),
            'messages_json':messages_json,
            'settings':settings,
            'po':po,
        }
        return render(request, self.template_name, context)

class ReceivePurchaseOrder(View, PermissionRequiredMixin, LoginRequiredMixin):
    permission_required = 'change_purchase_order'

    def get(self, request, id, *args, **kwargs):
        po = PurchaseOrder.objects.get(id=id)
        if po.status != 'approved':
            po.status = 'approved'
            po.received_date = timezone.now()
            po.save()
            messages.success(request, f'purchase order with number {po.order_number} received successfully')
        return redirect('purchase-management')
    
class CancellPurchaseOrder(View, PermissionRequiredMixin, LoginRequiredMixin):
    permission_required = 'change_purchase_order'

    def get(self, request, id, *args, **kwargs):
        po = PurchaseOrder.objects.get(id=id)
        if po.status != 'cancelled':
            po.status = 'cancelled'
            po.cancelled_date = timezone.now()
            po.save()
            messages.success(request, f'purchase order with number {po.order_number} cancelled successfully')
        return redirect('purchase-management')
    
class SinglePurchaseReport(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'purchase/detail_report.html'
    permission_required = 'purchase.view_purchaseorder'

    def get(self, request, id, *args, **kwargs):
        # 1. Fetch the PurchaseOrder or return 404
        purchase = get_object_or_404(PurchaseOrder, id=id)

        # 2. Render HTML template with context
        context = {
            'purchase': purchase,
            'request': request,  # required for absolute static/media URLs
        }
        html = render_to_string(self.template_name, context)

        # 3. Create PDF from HTML
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="purchase-Invoice.pdf"'

        # Create a BytesIO buffer
        result = BytesIO()

        # Convert HTML to PDF
        pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), dest=result,
            encoding='UTF-8', link_callback=self.link_callback)

        if pdf.err:
            return HttpResponse(f"Error generating PDF: <pre>{pdf.err}</pre>")

        # 4. Write result to response
        response.write(result.getvalue())
        return response

    def link_callback(self, uri, rel):
        """
        Convert HTML URIs to absolute system paths so xhtml2pdf can access those resources (e.g. images, CSS).
        """
        if uri.startswith(settings.MEDIA_URL):
            path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
        elif uri.startswith(settings.STATIC_URL):
            path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
        else:
            return uri  # return unchanged

        if not os.path.isfile(path):
            raise Exception(f'Media path does not exist: {path}')
        return path

class PendingPurchaseOrder(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'purchase/pending.html'
    permission_required = 'inventory.view_purchase_order'

    def get(self, request, *args, **kwargs):
        now = timezone.datetime.now()
        messages_data = [{'messages':message.message,'tags':message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)
        settings = Settings.objects.first()
        po = PurchaseOrder.objects.filter(status='pending')
        context = {
            'time':now,
            'year':now.year,
            'month':now.strftime('%B'),
            'day':now.strftime('%A'),
            'messages_json':messages_json,
            'settings':settings,
            'po':po
            }
        return render(request, self.template_name, context)
    
class ApprovePurchaseOrder(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'purchase/approve.html'
    permission_required = 'inventory.view_purchase_order'

    def get(self, request, *args, **kwargs):
        now = timezone.datetime.now()
        messages_data = [{'messages':message.message,'tags':message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)
        settings = Settings.objects.first()
        po = PurchaseOrder.objects.filter(status='approved')
        context = {
            'time':now,
            'year':now.year,
            'month':now.strftime('%B'),
            'day':now.strftime('%A'),
            'messages_json':messages_json,
            'settings':settings,
            'po':po
            }
        return render(request, self.template_name, context)
    
class approvedPurchaseOrderItems(View, PermissionRequiredMixin, LoginRequiredMixin):
    template_name = 'purchase/approvedItems.html'
    permission_required = ''
    
    def get(self, request, *args, **kwargs):
        now = timezone.datetime.now()
        messages_data = [{'messages':message.message,'tags':message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)
        settings = Settings.objects.first()
        approved_items = PurchaseItem.objects.filter(purchase_order__status='approved').select_related(
            'purchase_order', 'vendor', 'material'
        )
        total_cost = approved_items.aggregate(total=Sum('price'))['total'] or 0
        context = {
            'time':now,
            'year':now.year,
            'month':now.strftime('%B'),
            'day':now.strftime('%A'),
            'messages_json':messages_json,
            'settings':settings,
            'approved_items': approved_items,
            'total_cost':total_cost
        }
        return render(request, self.template_name, context)
    
class cancelledPurchaseOrderItems(View, PermissionRequiredMixin, LoginRequiredMixin):
    template_name = 'purchase/cancelledItems.html'
    permission_required = ''
    
    def get(self, request, *args, **kwargs):
        now = timezone.datetime.now()
        messages_data = [{'messages':message.message,'tags':message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)
        settings = Settings.objects.first()
        cancelled_items = PurchaseItem.objects.filter(purchase_order__status='cancelled').select_related(
            'purchase_order', 'vendor', 'material'
        )
        total_cost = cancelled_items.aggregate(total=Sum('price'))['total'] or 0
        context = {
            'time':now,
            'year':now.year,
            'month':now.strftime('%B'),
            'day':now.strftime('%A'),
            'messages_json':messages_json,
            'settings':settings,
            'cancelled_items': cancelled_items,
            'total_cost':total_cost
        }
        return render(request, self.template_name, context)

class PurchaseReport(View, LoginRequiredMixin, PermissionRequiredMixin):
    template_name = 'purchase/report.html'
    permission_required = 'purchase.view_purchasereport'

    def post(self, request, *args, **kwargs):
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        export_format = request.POST.get('format', 'pdf')  # default to pdf

        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                start_datetime = datetime.combine(start_date, datetime.min.time())
                end_datetime = datetime.combine(end_date + timedelta(days=1), datetime.min.time())

                purchase_orders = PurchaseOrder.objects.filter(
                    status='approved',
                    received_date__gte=start_datetime,
                    received_date__lt=end_datetime
                )

                total_cost = sum(p.total_cost for p in purchase_orders)

                if export_format == 'excel':
                    return self.generate_excel(purchase_orders, start_date_str, end_date_str, total_cost)

                # Otherwise, generate PDF
                context = {
                    'start_date': start_date_str,
                    'end_date': end_date_str,
                    'purchase_orders': purchase_orders,
                    'total_cost': total_cost
                }

                template = render_to_string('purchase/report.html', context)
                response = HttpResponse(content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="purchase_report.pdf"'

                result = pisa.pisaDocument(BytesIO(template.encode("UTF-8")), dest=response, link_callback=self.link_callback)
                if result.err:
                    return HttpResponse(f"We had some error: <pre>{str(result.err)}</pre>")

                return response

            except ValueError:
                return HttpResponse('Invalid date format.')

        return HttpResponse('No valid date was selected.')

    def generate_excel(self, purchase_orders, start_date, end_date, total_cost):
        wb = Workbook()
        ws = wb.active
        ws.title = "Purchase Report"

        # Report title and date range
        ws.append(['Purchase Report'])
        ws.append([f'Date Range: {start_date} to {end_date}'])
        ws.append([f"status: {p.status}" for p in purchase_orders]) 
        ws.append([])

        # Column headers for purchase orders
        ws.append(['Purchase Order ID'])

        for po in purchase_orders:
            # Purchase order main row
            ws.append([
                po.order_number,
            ])

            # Header row for items
            ws.append(['', 'MATERIAL', 'QUANTITY(qts)', 'UNIT_PRICE(p)', 'TOTAL'])

            # Purchase order items
            for item in po.items.all():  # Assuming related_name='items'
                total_price = item.quantity * item.unit_price
                ws.append([
                    '',
                    str(item.material.name),
                    item.quantity,
                    float(item.unit_price),
                    float(total_price)
                ])

            # Blank row after each purchase order
            ws.append([])

        # Total cost at the bottom
        ws.append([])
        ws.append(['', '', '', 'Total Purchase Cost:', float(total_cost)])

        # Auto-fit columns
        for column_cells in ws.columns:
            max_length = 0
            column = column_cells[0].column_letter
            for cell in column_cells:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            ws.column_dimensions[column].width = max_length + 2

        # Prepare response
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=purchase_report.xlsx'
        return response

    def link_callback(self, uri, rel):
        if uri.startswith(settings.MEDIA_URL):
            path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
        elif uri.startswith(settings.STATIC_URL):
            path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
        else:
            return uri
        if not os.path.isfile(path):
            raise Exception(f'Media path does not exist: {path}')
        return path



# PRODUCTMANAGEMENT
    
class ProductManagement(View,LoginRequiredMixin,PermissionRequiredMixin):
    template_name='Product/management.html'
    permission_required=''

    def get (self,request,*args,**kwargs):
        settings = Settings.objects.first()
        products=Product.objects.all()
        materials = Material.objects.all()
        now=datetime.now()
        messages_data=[{'message': message.message, 'tags': message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)


        context={
            'products':products,
            'time':now,
            'day':now.strftime('%A'),
            'month':now.strftime('%B'),
            'year':now.year,
            'messages_json':messages_json,
            'materials':materials,
            'settings':settings
        }

        return render(request, self.template_name,context)

    def post(self, request, *args, **kwargs):
        products = request.POST.getlist('product[]')
        quantities = request.POST.getlist('quantity[]')
        descriptions = request.POST.getlist('description[]')
        wholesale_prices = request.POST.getlist('wholesale_price[]')
        retail_prices = request.POST.getlist('retail_price[]')
        threshold_quantities = request.POST.getlist('threshold_quantity[]')

        # Check list length consistency
        if not all(len(lst) == len(products) for lst in [quantities, descriptions, wholesale_prices, retail_prices, threshold_quantities]):
            messages.error(request, "Mismatch in submitted form data.")
            return redirect('product-management')

        try:
            with transaction.atomic():
                for i in range(len(products)):
                    material = get_object_or_404(Material, id=products[i])

                    # Check if a product for this material already exists
                    if Product.objects.filter(product=material).exists():
                        messages.warning(request, f"Product for material '{material.name}' already exists and was skipped.")
                        return redirect('product-management')
                        

                    try:
                        quantity = int(quantities[i])
                        threshold_quantity = int(threshold_quantities[i])
                        wholesale_price = float(wholesale_prices[i])
                        retail_price = float(retail_prices[i])
                    except (ValueError, TypeError):
                        messages.error(request, f"Invalid data for material '{material.name}'. Skipping.")
                        continue

                    # Ensure enough stock is available
                    if material.quantity < quantity:
                        messages.error(request, f"Not enough stock for material '{material.name}'.")
                        continue

                    # Create new product
                    product = Product(
                        product=material,
                        quantity=quantity,
                        description=descriptions[i],
                        wholesale_price=wholesale_price,
                        retail_price=retail_price,
                        threshold_quantity=threshold_quantity
                    )

                    product.save()

            messages.success(request, "Product creation completed.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

        return redirect('product-management')

class UpdateDeleteProduct(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = ''

    def post(self, request, id, *args, **kwargs):
        product = get_object_or_404(Product, id=id)

        # # Store the old quantity for comparison
        # old_quantity = product.quantity

        # Get new values
        new_retail_price = request.POST['retail_price']
        new_wholesale_price = request.POST['wholesale_price']
        new_quantity = int(request.POST['quantity'])

        # Update product
        product.retail_price = new_retail_price
        product.wholesale_price = new_wholesale_price
        product.quantity = new_quantity
        product.save()  # This will now trigger your stock adjustment

        messages.success(request, 'Product updated successfully')
        return redirect('product-management')

    def get(self, request, id, *args, **kwargs):
        Product.objects.get(id=id).delete()
        messages.success(request, 'Product deleted successfully')
        return redirect('product-management')

class OrderManagementView(View,PermissionRequiredMixin,LoginRequiredMixin):
    template_name = 'order/management.html'
    permission_required = 'inventory.view_order'

    def get(self, request, *args, **kwargs):
        now = timezone.datetime.now()
        messages_data = [{'messages':message.message,'tags':message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)
        settings = Settings.objects.first()
        orders = Order.objects.all()
        context = {
            'time':now,
            'year':now.year,
            'month':now.strftime('%B'),
            'day':now.strftime('%A'),
            'messages_json':messages_json,
            'settings':settings,
            'products': Product.objects.all(),
            'orders':orders
            }
        return render(request, self.template_name, context)
 
    def post(self, request, *args, **kwargs):
        order_type = request.POST.get('order_type')
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')

        if not order_type or order_type not in ['retail', 'wholesale']:
            messages.error(request, "Invalid order type.")
            return redirect('order-management')

        if not product_ids or not quantities or len(product_ids) != len(quantities):
            messages.error(request, "Missing or mismatched order item data.")
            return redirect('order-management')

        try:
            with transaction.atomic():
                # ✅ Create the order (order_id will be auto-generated in model's save())
                order = Order.objects.create(
                    order_type=order_type,
                    status='pending',
                    user = request.user
                )

                for i in range(len(product_ids)):
                    product = get_object_or_404(Product, id=product_ids[i])

                    try:
                        quantity = int(quantities[i])
                        if quantity <= 0:
                            raise ValueError("Quantity must be positive.")
                    except ValueError:
                        messages.error(request, f"Invalid quantity for product {product.name}.")
                        raise

                    # ✅ OrderItem save() will trigger update_total
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity,
                    )

                # Optional: Recalculate to ensure it's correct
                order.update_total()

            messages.success(request, f"Order {order.order_id} created successfully.")

        except Exception as e:
            messages.error(request, f"Failed to create order: {str(e)}")

        return redirect('order-management')

class ApproveOrderManagementView(View, PermissionRequiredMixin, LoginRequiredMixin):
    permission_required = ''

    def get(self, request, id, *args, **kwargs):
        order = get_object_or_404(Order, id=id)
        if order.status != 'approved':
            order.status = 'approved'
            order.approved_date = datetime.now()
            order.save()
            messages.success(request, 'order with ID f{oredr.order_id} approved successfully')
            return redirect('order-management')
        
class CancellOrderManagementView(View, PermissionRequiredMixin, LoginRequiredMixin):
    permission_required = ''

    def get(self, request, id, *args, **kwargs):
        order = get_object_or_404(Order, id=id)
        if order.status != 'cancelled':
            order.status = 'cancelled'
            order.cancelled_date = datetime.now()
            order.save()
            messages.success(request, 'order with ID f{oredr.order_id} cancelled successfully')
            return redirect('order-management')