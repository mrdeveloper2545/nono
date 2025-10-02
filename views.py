from django.shortcuts import render, redirect, get_list_or_404, get_object_or_404
from stock.models import Unit,Settings,Material,Category,Vendor,Store,Purchase,Product,Wastage,Order
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
from .serializers import  ProductSerializer
from rest_framework import viewsets
from django.db.models.functions import TruncDate
from django.utils.dateparse import parse_date
from django.contrib.auth.models import User





# Create your views here.

# UNIT MANAGEMENT VIEW
class UnitManagement(View,PermissionRequiredMixin,LoginRequiredMixin):
    template_name='unit/management.html'
    permission_required='stock.view_unit'

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
    permission_required = 'stock.view_category'

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
    permission_required = ''

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
    permission_required = ''

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
    permission_required = ''

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

class AddMaterialToVendor(View, LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = ''
    template_name = 'vendor/material.html'

    def get(self, request, id, *args, **kwargs):
        materials = get_list_or_404(Material)
        vendor = get_object_or_404(Vendor,id=id)

        context = {
            'materials':materials,
            'vendor':vendor,

        }
        return render(request, self.template_name, context)

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




# STORE MANAGEMENT VIEW

class StoreManagement(View, LoginRequiredMixin, PermissionRequiredMixin):
    template_name = 'store/management.html'
    permission_required = ''


    def get(self, request, *args, **kwargs):
        stores = Store.objects.all()
        now = timezone.datetime.now()
        messages_data = [{'messages':message.message, 'tags':message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)
        settings = Settings.objects.first()

        context = {
            'stores':stores,
            'time':now,
            'day':now.strftime('%A'),
            'year':now.year,
            'month':now.strftime('%B'),
            'messages_json':messages_json,
            'settings':settings
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        names = request.POST.getlist('name[]')
        main_stores = 'main_store' in request.POST

        if not names:
            messages.info(request, 'No names has been provided')
            return redirect('store-management')

        if Store.objects.filter(name__in=names).exists():
            messages.info(request, 'One or more store already exist')
            return redirect('store-management')

        user = request.user
        stores = []

        for name in names:
            store = Store(name=name,user=user,main_store=main_stores)
            stores.append(store)

        Store.objects.bulk_create(stores)
        messages.success(request, 'store generated successfully')
        return redirect('store-management')

class UpdateDeleteStore(View, LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = ''


    def get(self, request, id, *args, **kwargs):
        Store.objects.get(id=id).delete()
        messages.success(request, 'store deleted successfully')
        return redirect('store-management')

    def post(self, request, id, *args, **kwargs):
        name = request.POST.get('name')
        Store.objects.filter(id=id).update(name=name)
        messages.success(request, 'store updated successfully')
        return redirect('store-management')

class BulkUpdateStore(View, LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = ''

    def post(self, request, *args, **kwargs):
        stores = get_list_or_404(Store)

        for store in stores:
            store.name = request.POST.get(f'name_{store.id}')

        Store.objects.bulk_update(stores,['name'])
        messages.success(request,'store updated successfully')
        return redirect('store-management')




# PURCHASES MANAGEMENT VIEW
class PurchaseItemManagement(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'purchase/management.html'
    permission_required = ''

    def get(self, request, *args, **kwargs):
        purchases = self.get_purchases()
        messages_json = self.get_messages_json(request)

        context = self.get_context_data(purchases, messages_json)
        return render(request, self.template_name, context)

    def get_purchases(self):
        cost_expression = ExpressionWrapper(
            F('price_variation') * F('quantity'),
            output_field=DecimalField()
        )

        return (
            Purchase.objects.annotate(truncated_date=TruncDate('date'))
            .values('date')
            .annotate(total_cost=Sum(cost_expression))
            .order_by('-date')
        )

    def get_messages_json(self, request):
        messages_data = [{'message': message.message, 'tags': message.tags} for message in messages.get_messages(request)]
        return json.dumps(messages_data) if messages_data else json.dumps([])

    def get_context_data(self, purchases, messages_json):
        now = datetime .now()
        materials = Material.objects.all()
        settings = Settings.objects.first()
        vendors = Vendor.objects.all()
        stores = Store.objects.filter(main_store=True)

        return {
            'purchases': purchases,
            'time': now,
            'year': now.year,
            'month': now.strftime('%B'),
            'day': now.strftime('%A'),
            'messages_json': messages_json,
            'materials':materials,
            'settings':settings,
            'vendors':vendors,
            'stores':stores
        }

    def post(self, request, *args, **kwargs):
        stores = request.POST.getlist('store[]')
        vendors = request.POST.getlist('vendor[]')
        names = request.POST.getlist("name[]")
        price_variations = request.POST.getlist("price_variation[]")
        quantities = request.POST.getlist("quantity[]")
        dates = request.POST.getlist("date[]")


        if not (len(names) == len(stores) == len(price_variations) == len(vendors)  == len(quantities) == len(dates)):
            messages.error(request, 'All fields must have the same number of entries.')
            return redirect('purchase-management')

        # List to hold Purchase instances for bulk creation
        purchases = []

        for i in range(len(names)):
            material = get_object_or_404(Material, id=names[i])
            vendor = get_object_or_404(Vendor, id=vendors[i])
            store = get_object_or_404(Store, id=stores[i])
            user = request.user

            purchase = Purchase(
                store=store,
                name=material,
                price_variation=price_variations[i],
                vendor=vendor,
                quantity=quantities[i],
                date=dates[i],
                user=user
            )
            purchases.append(purchase)

        Purchase.objects.bulk_create(purchases)

        messages.success(request, 'Purchases added successfully')
        return redirect('pending-purchase')

class ViewPurchase(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'purchase/view_purchase.html'
    permission_required = 'stock.view_purchase'

    def get(self, request, truncated_date, *args, **kwargs):
        settings = Settings.objects.first()
        purchases = Purchase.objects.filter(date=truncated_date)
        units=Unit.objects.all()
        categories=Category.objects.all()
        materials = get_list_or_404(Material)
        vendors = get_list_or_404(Vendor)
        now=datetime.now()

        if not purchases.exists():
            return render(request, 'purchase/no_purchases.html', {'truncated_date': truncated_date})

        total_cost = sum(purchase.price_variation * purchase.quantity for purchase in purchases)

        context = {
            'time': now,
            'year': now.year,
            'month': now.strftime('%B'),
            'day': now.strftime('%A'),
            'purchases': purchases,
            'truncated_date': truncated_date,
            'total_cost': total_cost,
            'units':units,
            'materials':materials,
            'categories':categories,
            'settings':settings,
            'vendors':vendors
        }

        return render(request, self.template_name, context)

class UpdateDeletePurchase(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'stock.change_purchase'
    template_name = 'purchase/view_purchase.html'

    def post(self, request, *args, **kwargs):
        purchase_id = kwargs.get('id')  # Get `id` from kwargs

        # Retrieve the specific purchase object based on `id`
        purchase = get_object_or_404(Purchase, id=purchase_id)

        # Extract data from the form
        names = request.POST.getlist('name[]')
        categories = request.POST.getlist('category[]')
        price_variations = request.POST.getlist('price_variation[]')
        quantities = request.POST.getlist('quantity[]')
        units = request.POST.getlist('unit[]')
        dates = request.POST.getlist('date[]')

        # Process each entry
        for i in range(len(names)):
            material = get_object_or_404(Material, id=names[i])
            category = get_object_or_404(Category, id=categories[i])
            unit = get_object_or_404(Unit, id=units[i])

            if i == 0:
                # Update the existing purchase for the first item
                purchase.name = material
                purchase.category = category
                purchase.price_variation = price_variations[i]
                purchase.quantity = quantities[i]
                purchase.unit = unit
                purchase.date = dates[i]
                purchase.save()
            else:
                # Create new purchase entries for additional items
                new_purchase = Purchase(
                    name=material,
                    category=category,
                    price_variation=price_variations[i],
                    quantity=quantities[i],
                    unit=unit,
                    date=dates[i],
                )
                new_purchase.save()

        # Provide success feedback to the user and redirect
        messages.success(request, "Purchase details updated successfully.")
        return redirect('pending-purchase')


    def get(self, request, id, *args, **kwargs):
        Purchase.objects.get(id=id).delete()
        messages.info(request, "purchase order deleted successfully")
        return redirect('pending-purchase')

class BulkPurchaseUpdate(View, LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = 'purchase.change_purchase'  # Set proper permission required
    template_name = 'purchase/purchase.html'

    def get(self, request, *args, **kwargs):
        # Fetch date from query string and parse it
        target_date_str = request.GET.get('date')
        target_date = parse_date(target_date_str) if target_date_str else None

        if target_date:
            # Filter purchases by the parsed date
            purchases = Purchase.objects.filter(date=target_date)
        else:
            purchases = Purchase.objects.all()  # Or handle the case if no date is provided

        return render(request, self.template_name, {'purchases': purchases})

    def post(self, request, *args, **kwargs):
        # Get lists of purchase IDs and other fields from the form data
        purchase_ids = request.POST.getlist('purchase_id')  # List of purchase IDs
        quantities = request.POST.getlist('quantity')  # List of quantities
        price_variations = request.POST.getlist('price_variation')  # List of price variations

        # Get categories using dynamic names like 'category_{{ purchase.id }}'
        categories = [
            request.POST.get(f'category_{purchase_id}') for purchase_id in purchase_ids
        ]  # List of category IDs as strings

        # Check if the lengths of all lists match
        if not (len(purchase_ids) == len(quantities) == len(price_variations) == len(categories)):
            return redirect('purchase-management')  # Handle mismatch if necessary

        # Use bulk updates in a more efficient way
        updated_purchases = []
        for purchase_id, quantity, price_variation, category in zip(purchase_ids, quantities, price_variations, categories):
            # Retrieve purchase, ensuring it exists
            purchase = get_object_or_404(Purchase, id=purchase_id)

            # Get the category object by its ID (only if the category exists)
            if category:  # Check if a valid category ID is provided
                category_obj = get_object_or_404(Category, id=category)  # Retrieve the category object
                purchase.category = category_obj  # Update the purchase category

            # Update the other fields
            purchase.quantity = quantity  # Update quantity
            purchase.price_variation = price_variation  # Update price variation

            # Add to the list of updated purchases
            updated_purchases.append(purchase)

        # Bulk update the updated purchases (make sure only valid fields are being updated)
        Purchase.objects.bulk_update(updated_purchases, ['quantity', 'price_variation', 'category'])

        # Redirect to the purchase management page after the update
        return redirect('purchase-management')

class ReceivedView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'stock.receive_purchase'

    def get(self, request, date):
        target_date = timezone.datetime.strptime(date, '%Y-%m-%d').date()

        purchases = Purchase.objects.filter(date=target_date, status='pending')

        if purchases.exists():
            for purchase in purchases:
                if purchase.status != 'received':
                    purchase.status = 'received'
                    purchase.received_date = timezone.now()
                    purchase.save()
            messages.success(request, f'{purchases.count()} purchase order(s) received on {timezone.now()}.')
        else:
            messages.warning(request, 'No pending purchase orders found for this date.')

        return redirect('purchase-received')

class CancelledView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'stock.cancel_purchase'

    def get(self, request, date):
        target_date = timezone.datetime.strptime(date, '%Y-%m-%d').date()

        purchases = Purchase.objects.filter(date=target_date, status='pending')

        if purchases.exists():
            for purchase in purchases:
                if purchase.status != 'cancelled':
                    purchase.status = 'cancelled'
                    purchase.cancelled_date = datetime.now()
                    purchase.save()
                    messages.success(request, f'{purchases.count()} purchase order(s) cancelled on {timezone.now()}.')
                else:
                    messages.warning(request, 'No pending purchase orders found for this date.')
        return redirect('cancelled-purchase')

class Pending(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'purchase/pending.html'
    permission_required = 'stock.view_purchase'

    def get(self, request, *args, **kwargs):
        settings = Settings.objects.first()
        purchases = Purchase.objects.filter(status='pending')
        units=Unit.objects.all()
        categories=Category.objects.all()
        now = datetime.now()
        materials = Material.objects.all()
        vendors = Vendor.objects.all()
        context={
            'purchases': purchases,
            'units':units,
            'categories':categories,
            'time': now,
            'year': now.year,
            'month': now.strftime('%B'),
            'day': now.strftime('%A'),
            'materials':materials,
            'settings':settings,
            'vendors':vendors
        }
        return render(request, self.template_name, context)

class Received(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'stock.receive_purchase'
    template_name = 'purchase/received.html'

    def get(self, request, *args, **kwargs):
        settings = Settings.objects.first()
        purchases = Purchase.objects.filter(status='received')

        now = datetime.now()

        context = {
            'purchases': purchases,
            'time': now,
            'year': now.year,
            'month': now.strftime('%B'),
            'day': now.strftime('%A'),
            'settings':settings
        }
        return render(request, self.template_name, context)

class Cancelled(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'stock.receive_purchase'
    template_name = 'purchase/cancelled.html'

    def get(self, request, *args, **kwargs):
        settings = Settings.objects.first()
        purchases = Purchase.objects.filter(status='cancelled')
        now = datetime.now()

        context = {
            'purchases': purchases,
            'time': now,
            'year': now.year,
            'month': now.strftime('%B'),
            'day': now.strftime('%A'),
            'settings':settings
        }
        return render(request, self.template_name, context)

# class BulkOpenStock(View,LoginRequiredMixin,PermissionRequiredMixin):
#     template_name = 'stock/open.html'
#     permission_required = ''

#     def get(self, request,*args, **kwargs):
#         settings = Settings.objects.first()
#         now = timezone.datetime.now()
#         messages_data = [{'messages':message.message, 'tags':message.tags} for message in messages.get_messages(request)]
#         messages_json = json.dumps(messages_data)
#         if not settings.inventory:
#             return HttpResponseForbidden("Inventory management is disabled.")

#         if settings.inventory:
#             opening_stock = (
#                 OpeningStock.objects
#                 .annotate(truncated_date=TruncDate('date'))
#                 .values('date',)
#                 .annotate(quantity=Sum('quantity'))
#                 .order_by('date',)
#             )
#             context={
#                 'opening_stock':opening_stock,
#                 'settings':settings,
#                 'time':now,
#                 'day':now.strftime('%A'),
#                 'month':now.strftime('%B'),
#                 'year':now.year,
#                 'messages_json':messages_json
#                 }
#         return render(request, self.template_name, context)

#     def post(self, request, *args, **kwargs):
#         settings = Settings.objects.first()
#         if settings.inventory:
#             materials = get_list_or_404(Material)
#             quantity = request.POST.get('quantity')
#             date = request.POST.get('date')
#             store = Store.objects.filter(main_store=True).first()

#             if not store:
#                 messages.error(request, "Main store not found.")
#                 return redirect('open-management')

#             opening_stocks_to_create = []
#             opening_stocks_to_update = []

#             for material in materials:
#                 open_stock = OpeningStock.objects.filter(material=material, store=store, date=date).first()

#                 if open_stock:
#                     if open_stock.quantity is None or open_stock.quantity == 0:
#                         open_stock.quantity = quantity
#                         open_stock.date = date
#                         opening_stocks_to_update.append(open_stock)
#                 else:
#                     opening_stocks_to_create.append(OpeningStock(
#                         material=material,
#                         quantity=quantity,
#                         date=date,
#                         user=request.user,
#                         store=store,
#                         manual_entry=True
#                     ))

#             if opening_stocks_to_create:
#                 OpeningStock.objects.bulk_create(opening_stocks_to_create)

#             if opening_stocks_to_update:
#                 OpeningStock.objects.bulk_update(opening_stocks_to_update, ['quantity', 'date'])

#         return redirect('open-management')
    
# class ViewOpenStock(LoginRequiredMixin, PermissionRequiredMixin, View):
#         template_name = 'stock/view_open_stock.html'
#         permission_required = ''

#         def get(self, request, truncated_date, *args, **kwargs):
#             settings = Settings.objects.first()
#             stock = OpeningStock.objects.filter(date=truncated_date)
#             now=datetime.now()

#             if not stock.exists():
#                 return render(request, 'purchase/no_purchases.html', {'truncated_date': truncated_date})

#             context = {
#                 'time': now,
#                 'year': now.year,
#                 'month': now.strftime('%B'),
#                 'day': now.strftime('%A'),
#                 'stock': stock,
#                 'truncated_date': truncated_date,
#                 'settings':settings,
#             }

#             return render(request, self.template_name, context)

class deleteAll(View,LoginRequiredMixin,PermissionRequiredMixin):
    permission_required=''
    def get(self,request,*args,**kwargs):
        Purchase.objects.filter(status='pending').delete()
        return redirect('purchase-management')

def purchase_report_pdf(request):
    # Fetch data from your model
    purchases = None
    start_date = None
    end_date = None
    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')

        if  start_date_str and end_date_str:

            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                purchases = Purchase.objects.filter(status='received',date__gte=start_date, date__lte=end_date)
                total_cost = sum(purchase.quantity * purchase.price_variation for purchase in purchases)


                # Define the context()
                context = {
                    'start_date':start_date,
                    'end_date':end_date,
                    'purchases': purchases,
                    'total_cost':total_cost
                }

                # Render the HTML template with the context
                template = render_to_string('purchase/report.html', context)

                # Create the HTTP response with PDF content type
                response = HttpResponse(content_type='application/pdf')
                response['Content-Disposition'] = 'attachment;filename="purchase_report.pdf"'

                # Convert HTML to PDF
                result = pisa.pisaDocument(BytesIO(template.encode("UTF-8")), dest=response)

                # Check if there were errors
                if result.err:
                    return HttpResponse(
                        f" we had some error: <pre>{str(result.err)}</pre>")

                return response
            except ValueError:
                return HttpResponse('invalid date format')
    return HttpResponse('No valid date was selected')

class SinglePurchaseReport(View, LoginRequiredMixin, PermissionRequiredMixin):
    template_name = 'purchase/detail_report.html'

    def get(self, request, id, *args, **kwargs):
        purchase = get_object_or_404(Purchase, id=id)
        context = {
            'purchase':purchase
        }
        template = render_to_string(self.template_name,context)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment;filename=purchase-order.pdf'

        result = pisa.pisaDocument(BytesIO(template.encode("UTF-8")),dest=response)

        if result.err:
            return HttpResponse(
                f"we had some error: <pre>{str(result.err)}</pre>"
            )
        return response




# SELLING PRODUCT VIEW
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
        prices = request.POST.getlist('price[]')

        for i in range(len(products)):
            material = get_object_or_404(Material, id=products[i])
            quantity = int(quantities[i])
            price = prices[i]
            description = descriptions[i]

            # Check if enough material is available
            if material.quantity < quantity:
                messages.error(request, f"Not enough stock for material '{material.name}'")
                return redirect('product-management')



            product = Product(
                product=material,
                quantity=quantity,
                description=description,
                price=price
            )

            product.save()  # Triggers save() method that adjusts material quantity

        messages.success(request, 'Products created successfully')
        return redirect('product-management')

class UpdateDeleteProduct(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = ''

    def post(self, request, id, *args, **kwargs):
        product = get_object_or_404(Product, id=id)

        # Store the old quantity for comparison
        old_quantity = product.quantity

        # Get new values
        new_price = request.POST['price']
        new_quantity = int(request.POST['quantity'])

        # Update product
        product.price = new_price
        product.quantity = new_quantity
        product.save()  # This will now trigger your stock adjustment

        messages.success(request, 'Product updated successfully')
        return redirect('product-management')

    def get(self, request, id, *args, **kwargs):
        Product.objects.get(id=id).delete()
        messages.success(request, 'Product deleted successfully')
        return redirect('product-management')


# ORDER MANAGEMENT VIEW
class OrderManagement(View,LoginRequiredMixin,PermissionRequiredMixin):
    template_name='Order/management.html'
    permission_required=''

    def get(self,request,*args,**kwargs):
        settings = Settings.objects.first()
        orders=Order.objects.annotate(truncated=TruncDate('date')).values('date').annotate(total_order_cost=Sum(
            ExpressionWrapper(F('quantity')*F('name__price'),output_field=DecimalField()))).order_by('-date')
        users=User.objects.all()
        products = Product.objects.all()
        now=datetime.now()
        messages_data=[{'message':messages.message, 'tags':messages.tags}for messages in messages.get_messages(request)]
        messages_json=json.dumps(messages_data)

        context={
            'time': now,
            'year': now.year,
            'month': now.strftime('%B'),
            'day': now.strftime('%A'),
            'orders':orders,
            'users':users,
            'products':products,
            'messages_json':messages_json,
            'settings':settings
        }
        return render(request, self.template_name,context)

    def post(self, request, *args, **kwargs):
        names = request.POST.getlist('name[]')
        quantities = request.POST.getlist("quantity[]")
        


        if not (len(names) == len(names) ==len(quantities)):
            messages.error(request, 'All fields must have the same number of entries.')
            return redirect('purchase-management')

        # List to hold Purchase instances for bulk creation
        orders = []

        for i in range(len(names)):
            name = get_object_or_404(Product, id=names[i])
            date = datetime.now()
            quantity = int(quantities[i])
            user=request.user

            order = Order(
                name=name,
                quantity=quantity,
                date=date,
                user=user
            )
            orders.append(order)

        Order.objects.bulk_create(orders)

        messages.success(request, 'Order created successfully')
        return redirect('order-management')

class ViewOrder(View,LoginRequiredMixin,PermissionRequiredMixin):
    template_name = 'Order/view.html'
    permission_required = ''

    def get(self, request, truncated, *args, **kwargs):
        settings = Settings.objects.first()
        order = Order.objects.filter(date=truncated)
        units=Unit.objects.all()
        categories=Category.objects.all()
        materials = get_list_or_404(Material)
        vendors = get_list_or_404(Vendor)
        now=datetime.now()
        

        context = {
            'time': now,
            'year': now.year,
            'month': now.strftime('%B'),
            'day': now.strftime('%A'),
            'order': order,
            'truncated': truncated,
            'units':units,
            'materials':materials,
            'categories':categories,
            'settings':settings,
            'vendors':vendors
        }

        return render(request, self.template_name, context)

class UpdateDeleteOrder(View,LoginRequiredMixin,PermissionRequiredMixin):
    permission_required=''

    def get(self,request,id,*args,**kwargs):
        Order.objects.get(id=id).delete()
        messages.success(request,'order deleted successfully')
        return redirect('order-management')

    def post(self,request,id,*args,**kwargs):
        quantity=request.POST['quantity']
        Order.objects.filter(id=id).update(quantity=quantity)
        messages.success(request, 'order updated successfully')
        return redirect('order-management')

class UserOrderManagement(View,PermissionRequiredMixin,LoginRequiredMixin):
    template_name='Order/user_order_management.html'
    permission_required='stock.view_purchase'

    def get(self,request,*args,**kwargs):
        user_order=Order.objects.filter(user=request.user)
        settings = Settings.objects.first()
        now=datetime.now()
        context={
            'time': now,
            'year': now.year,
            'month': now.strftime('%B'),
            'day': now.strftime('%A'),
            'user_order':user_order,
            'settings':settings
            }
        return render(request, self.template_name, context)

    def post(self,request,*args,**kwargs):
        name_id=request.POST['name']
        quantity=request.POST['quantity']
        date=datetime.now()
        user=request.user

        product=get_object_or_404(Product, id=name_id)

        Order.objects.create(name=product,user=user,quantity=quantity,date=date)
        messages.success(request, 'order crested successfully')
        return redirect('user-order-management')

class ChargedOrder(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'yourapp.change_order'  # <-- Set correct permission here

    def get(self, request, truncated):
        try:
            truncated_date = timezone.datetime.strptime(truncated, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date format.')
            return redirect('order-management')

        orders = Order.objects.filter(date=truncated_date, status='pending')

        if not orders.exists():
            messages.warning(request, 'No pending orders found for the given date.')
        else:
            updated = False
            for order in orders:
                order.status = 'charged'
                order.save()
                updated = True

            if updated:
                messages.success(request, 'All pending orders marked as charged.')
            else:
                messages.warning(request, 'No pending orders were updated.')

        return redirect('order-management')

class VoidedOrder(View,LoginRequiredMixin,PermissionRequiredMixin):
 def get(self, request, truncated):
        try:
            truncated_date = timezone.datetime.strptime(truncated, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date format.')
            return redirect('order-management')

        orders = Order.objects.filter(date=truncated_date, status='pending')

        if not orders.exists():
            messages.warning(request, 'No pending orders found for the given date.')
        else:
            updated = False
            for order in orders:
                order.status = 'voided'
                order.save()
                updated = True

            if updated:
                messages.success(request, ' order marked as voided.')
            else:
                messages.warning(request, 'No pending orders were updated.')

        return redirect('order-management')

def order_report_pdf(request):
    # Fetch data from your model
    orders = None
    start_date = None
    end_date = None
    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')

        if  start_date_str and end_date_str:

            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                orders = Order.objects.filter(status='charged',date__gte=start_date, date__lte=end_date)
                total_cost = sum(order.quantity * order.name.price for order in orders)


                # Define the context()
                context = {
                    'start_date':start_date,
                    'end_date':end_date,
                    'orders': orders,
                    'total_cost':total_cost
                }

                # Render the HTML template with the context
                template = render_to_string('Order/report.html', context)

                # Create the HTTP response with PDF content type
                response = HttpResponse(content_type='application/pdf')
                response['Content-Disposition'] = 'attachment;filename="order_report.pdf"'

                # Convert HTML to PDF
                result = pisa.pisaDocument(BytesIO(template.encode("UTF-8")), dest=response)

                # Check if there were errors
                if result.err:
                    return HttpResponse(
                        f" we had some error: <pre>{str(result.err)}</pre>")

                return response
            except ValueError:
                return HttpResponse('invalid date format')
    return HttpResponse('No valid date was selected')




# WASTAGE MANAGEMENT VIEW
class wastageManagement(View,LoginRequiredMixin,PermissionRequiredMixin):
    template_name='wastage/management.html'
    permission_required=''

    def get(self,request,*args,**kwargs):
        settings = Settings.objects.first()
        wastages=Wastage.objects.all()
        purchases=Purchase.objects.filter(status='received')
        now=datetime.now()

        messages_data=[{'message':messages.message, 'tags':messages.tags} for messages in messages.get_messages(request)]
        messages_json=json.dumps(messages_data)

        context={
            'time':now,
            'wastages':wastages,
            'purchases':purchases,
            'messages_json':messages_json,
            'month':now.strftime('%B'),
            'day':now.strftime('%A'),
            'year':now.year,
            'settings':settings
        }
        return render(request,self.template_name,context)


    def post(self,request,*args,**kwargs):
        name_id=request.POST['name']
        quantity=request.POST['quantity']
        date=datetime.now()

        purchase=get_object_or_404(Purchase,id=name_id)
        Wastage.objects.create(name=purchase,quantity=quantity,date=date)
        messages.success(request,'wastage product created successfully')
        return redirect('wastage-management')


class deleteUpdateWastage(View,LoginRequiredMixin,PermissionRequiredMixin):
    permission_required=''

    def get(self,request,id,*args,**kwargs):
        Wastage.objects.get(id=id).delete()
        messages.success(request,'wastage product deleted successfully')
        return redirect('wastage-management')


    def post(self,request,id,*args,**kwargs):
        quantity=request.POST['quantity']
        Wastage.objects.filter(id=id).update(quantity=quantity)
        messages.success(request,'wastage product updated successfully')
        return redirect('wastage-management')


# API VIEW
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer