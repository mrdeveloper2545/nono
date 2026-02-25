from django.shortcuts import render,redirect,get_object_or_404,get_list_or_404
from django.views import View
from django.contrib.auth import authenticate, login,logout
from django.contrib.auth.models import User,Permission,Group
from django.contrib.auth.mixins import PermissionRequiredMixin,LoginRequiredMixin
from django.contrib import messages
import calendar
from collections import defaultdict
from dashboard.models import *
from inventory.models import *
from django.db.models.functions import TruncMonth,TruncDay,TruncDate
from django.db.models import ExpressionWrapper,F,FloatField,Sum,DecimalField,Count
import json
from datetime import datetime, timedelta
from django.utils import  timezone
from decimal import Decimal
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.contrib.auth import update_session_auth_hash
from django.utils.encoding import force_str
from django.conf import settings
from decimal import Decimal
import pytz
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from xhtml2pdf import pisa
from io import BytesIO





class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


# Create your views here.

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password')
            return redirect('login')
    else:
        return render(request, 'auth/login.html')

def password_reset(request):
    if request.method == "POST":
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = None

        if user:
            # Generate password reset link
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_link = request.build_absolute_uri(
                f"/reset/{uid}/{token}/"
            )

            # Send email
            subject = "Password Reset Request"
            message = render_to_string('auth/email_password.html', {
                'user': user,
                'reset_link': reset_link,
            })
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

            messages.success(request, "A password reset link has been sent to your email.")
        else:
            messages.error(request, "No account found with that email.")

        return redirect('password-reset')

    return render(request, 'auth/password_reset.html')

def custom_password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_object_or_404(User, pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')

            if not new_password1 or not new_password2:
                messages.error(request, "Both password fields are required.")
            elif new_password1 != new_password2:
                messages.error(request, "Passwords do not match.")
            else:
                user.set_password(new_password1)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Your password has been set successfully.")
                return redirect('login')
        else:

            pass
    else:
        messages.error(request, "The password reset link is invalid or has expired.")
        return redirect('password-reset')

    return render(request, 'auth/custom_set_password.html')

def logout_view(request):
    logout(request)
    return redirect('login')


class ChangePasswordView(LoginRequiredMixin, View): 
    template_name = 'navbar.html'

    def get(self, request, *args, **kwargs):
        settings = Settings.objects.first()
        messages_data = [{'message': message.message, 'tags': message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)

        context = {
            'messages_json': messages_json,
            'settings': settings,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')

        user = request.user
        errors = {}

        if not user.check_password(old_password):
            errors['old_password'] = "Old password is incorrect."
            return redirect('home')

        if new_password1 != new_password2:
            errors['new_password2'] = "The new passwords do not match."
            return redirect('home')

        try:
            validate_password(new_password1, user)
        except ValidationError as e:
            errors['new_password1'] = e.messages[0]

        if not errors:
            user.set_password(new_password1)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password was successfully updated.")
            return redirect('user-profile')
        else:
            settings = Settings.objects.first()
            messages_data = [{'message': message.message, 'tags': message.tags} for message in messages.get_messages(request)]
            messages_json = json.dumps(messages_data)

            context = {
                'messages_json': messages_json,
                'settings': settings,
                'errors': errors,
                'old_password': old_password,
                'new_password1': new_password1,
                'new_password2': new_password2,
            }
            return render(request, self.template_name, context)




def Dashboard(request):
    # -----------------------------
    # DATE & TIME SETUP
    # -----------------------------
    now = timezone.now()
    today = now.date()
    yesterday = today - timedelta(days=1)
    settings = Settings.objects.first()

    # -----------------------------
    # YEAR FILTER FOR MONTHLY CHART
    # -----------------------------
    selected_year = request.GET.get("year")
    try:
        selected_year = int(selected_year)
    except (TypeError, ValueError):
        selected_year = today.year

    available_years = Order.objects.dates("order_date", "year")  # years with orders

    # -----------------------------
    # DATE FILTER FOR DAILY TOTALS / DOUGHNUT CHART
    # -----------------------------
    start_date = end_date = today
    if request.method == "POST":
        filter_date_str = request.POST.get("filter")
        if filter_date_str:
            try:
                filter_date = datetime.strptime(filter_date_str, "%Y-%m-%d").date()
                start_date = end_date = filter_date
            except ValueError:
                pass

    # -----------------------------
    # BASE QUERYSETS
    # -----------------------------
    approved_orders = Order.objects.filter(status="approved")
    received_purchases = PurchaseOrder.objects.filter(status="approved")

    # Expressions for sums
    income_expr = ExpressionWrapper(
        F("quantity") * F("product__retail_price"), output_field=FloatField()
    )
    purchase_expr = ExpressionWrapper(
        F("quantity") * F("price"), output_field=FloatField()
    )

    # -----------------------------
    # DAILY STATS
    # -----------------------------
    # Orders today and yesterday
    order_counts = approved_orders.filter(
        approved_date__date__in=[today, yesterday]
    ).values("approved_date").annotate(total=Count("id"))
    order_dict = {o["approved_date"]: o["total"] for o in order_counts}
    today_order = order_dict.get(today, 0)
    yesterday_order = order_dict.get(yesterday, 0)
    order_rate = ((today_order - yesterday_order) / yesterday_order * 100) if yesterday_order else (100 if today_order else 0)

    # Income today/yesterday
    income_data = OrderItem.objects.filter(
        order__status="approved", order__approved_date__date__in=[today, yesterday]
    ).annotate(total=ExpressionWrapper(F("quantity") * F("product__retail_price"), output_field=FloatField())
    ).values("order__approved_date").annotate(total_sum=Sum("total"))

    income_dict = {i["order__approved_date"]: i["total_sum"] or 0 for i in income_data}
    today_income = income_dict.get(today, 0)
    yesterday_income = income_dict.get(yesterday, 0)
    income_rate = ((today_income - yesterday_income) / yesterday_income * 100) if yesterday_income else (100 if today_income else 0)

    # Purchases today/yesterday
    purchase_data = PurchaseItem.objects.filter(
        purchase_order__status="approved", purchase_order__received_date__date__in=[today, yesterday]
    ).annotate(total=ExpressionWrapper(F("quantity") * F("price"), output_field=FloatField())
    ).values("purchase_order__received_date").annotate(total_sum=Sum("total"))

    purchase_dict = {p["purchase_order__received_date"]: p["total_sum"] or 0 for p in purchase_data}
    today_purchase = purchase_dict.get(today, 0)
    yesterday_purchase = purchase_dict.get(yesterday, 0)
    purchase_rate = ((today_purchase - yesterday_purchase) / yesterday_purchase * 100) if yesterday_purchase else (100 if today_purchase else 0)

    # Total orders, income, purchases for selected day
    total_order = approved_orders.filter(approved_date__date__range=[start_date, end_date]).count()
    total_income = OrderItem.objects.filter(
        order__status="approved", order__approved_date__date__range=[start_date, end_date]
    ).aggregate(total=Sum(F("quantity") * F("product__retail_price"), output_field=FloatField()))["total"] or 0
    total_purchases = PurchaseItem.objects.filter(
        purchase_order__status="approved", purchase_order__received_date__date__range=[start_date, end_date]
    ).aggregate(total=Sum(F("quantity") * F("price"), output_field=FloatField()))["total"] or 0

    # -----------------------------
    # MONTHLY CHARTS
    # -----------------------------
    monthly_sales = OrderItem.objects.filter(
        order__status="approved", order__approved_date__year=selected_year
    ).annotate(month=TruncMonth("order__approved_date")).values("month").annotate(total=Sum(F("quantity") * F("product__retail_price"), output_field=FloatField())).order_by("month")

    monthly_purchase = PurchaseItem.objects.filter(
        purchase_order__status="approved", purchase_order__received_date__year=selected_year
    ).annotate(month=TruncMonth("purchase_order__received_date")).values("month").annotate(total=Sum(F("quantity") * F("price"), output_field=FloatField()))

    month_abbr = [calendar.month_abbr[i].upper() for i in range(1, 13)]
    sales_totals = defaultdict(float)
    purchase_totals = defaultdict(float)

    for item in monthly_sales:
        month_name = month_abbr[item["month"].month - 1]
        sales_totals[month_name] += item["total"] or 0

    for item in monthly_purchase:
        month_name = month_abbr[item["month"].month - 1]
        purchase_totals[month_name] += item["total"] or 0

    sales_totals_list = [sales_totals[m] for m in month_abbr]
    purchase_totals_list = [purchase_totals[m] for m in month_abbr]

    # -----------------------------
    # WEEKLY SALES
    # -----------------------------
    start_of_week = today - timedelta(days=today.weekday())
    start_of_last_week = start_of_week - timedelta(days=7)
    end_of_week = start_of_week + timedelta(days=6)
    end_of_last_week = start_of_week - timedelta(days=1)

    weekly_sales = OrderItem.objects.filter(
        order__status="approved", order__approved_date__date__range=[start_of_last_week, end_of_week]
    ).annotate(day=TruncDay("order__approved_date")).values("day").annotate(total=Sum(F("quantity") * F("product__retail_price"), output_field=FloatField()))

    this_week_data = defaultdict(float)
    last_week_data = defaultdict(float)
    for sale in weekly_sales:
        sale_day = sale["day"]
        total = sale["total"] or 0
        if start_of_week <= sale_day.date() <= end_of_week:
            this_week_data[(sale_day.date() - start_of_week).days] = total
        elif start_of_last_week <= sale_day.date() <= end_of_last_week:
            last_week_data[(sale_day.date() - start_of_last_week).days] = total

    this_week_totals = [this_week_data.get(i, 0) for i in range(7)]
    last_week_totals = [last_week_data.get(i, 0) for i in range(7)]
    day_labels = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

    # -----------------------------
    # TOP PRODUCTS
    # -----------------------------
    # Daily top
    daily_top_products = OrderItem.objects.filter(
        order__status='approved',
        order__approved_date__date__range=[start_date, end_date]
    ).values('product__product__name').annotate(
        total_sales=Sum(F('quantity') * F('product__retail_price'), output_field=FloatField())
    ).order_by('-total_sales')[:5]

    # Weekly top
    weekly_top_products = OrderItem.objects.filter(
        order__status='approved',
        order__approved_date__date__range=[start_of_week, end_of_week]
    ).values('product__product__name').annotate(
        total_sales=Sum(F('quantity') * F('product__retail_price'), output_field=FloatField())
    ).order_by('-total_sales')[:5]

    # Monthly top
    monthly_top_products = OrderItem.objects.filter(
        order__status='approved',
        order__approved_date__year=today.year
    ).values('product__product__name').annotate(
        total_sales=Sum(F('quantity') * F('product__retail_price'), output_field=FloatField())
    ).order_by('-total_sales')[:5]

    # -----------------------------
    # CONTEXT
    # -----------------------------
    context = {
        "total_order": total_order,
        "total_income": total_income,
        "purchases": total_purchases,
        "order_rate": order_rate,
        "income_rate": income_rate,
        "purchases_rate": purchase_rate,
        "sales_totals": json.dumps(sales_totals_list),
        "purchase_totals": json.dumps(purchase_totals_list),
        "months": json.dumps(month_abbr),
        "this_week_totals": json.dumps(this_week_totals),
        "last_week_totals": json.dumps(last_week_totals),
        "day_labels": json.dumps(day_labels),
        "top_product_labels": json.dumps([p['product__product__name'] for p in daily_top_products]),
        "top_product_totals": json.dumps([p['total_sales'] or 0 for p in daily_top_products]),
        "weekly_top_product_labels": json.dumps([p['product__product__name'] for p in weekly_top_products]),
        "weekly_top_product_totals": json.dumps([p['total_sales'] or 0 for p in weekly_top_products]),
        "monthly_top_product_labels": json.dumps([p['product__product__name'] for p in monthly_top_products]),
        "monthly_top_product_totals": json.dumps([p['total_sales'] or 0 for p in monthly_top_products]),
        "selected_year": selected_year,
        "available_years": available_years,
        "time": now,
        "settings": settings,
        "filter": start_date
    }

    return render(request, "dashboard/home.html", context)


class UserManagement(PermissionRequiredMixin,LoginRequiredMixin, View):
    template_name = 'auth/users.html'
    permission_required=''

    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            username = request.POST['username']
            first_name = request.POST['first_name']
            last_name = request.POST['last_name']
            email = request.POST['email']
            password = request.POST['password']
            confirm_password = request.POST['password']

            if not password:
                password = email
                confirm_password = email

            if password != confirm_password:
                messages.error(request, 'Passwords do not match')
                return self.get(request, *args, **kwargs)

            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists')
                return self.get(request, *args, **kwargs)

            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists')
                return self.get(request, *args, **kwargs)

            user=User.objects.create_user(username=username,first_name=first_name,last_name=last_name,email=email,password=password)
            user.save()
            messages.success(request, 'User created successfully')
            return redirect('users')


    def get(self, request, *args, **kwargs):
        groups=Group.objects.all()
        users = User.objects.all()
        now=timezone.datetime.now()
        settings = Settings.objects.first()
        messages_data = [{'message': message.message, 'tags': message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)

        context={
            'users':users,
            'groups':groups,
            'time':now,
            'day':now.strftime('%A'),
            'second':now.second,
            'minute':now.minute,
            'hour':now.hour,
            'month':now.strftime('%B'),
            'year':now.year,
            'settings':settings,
            'messages_json':messages_json
            }
        return render(request, self.template_name, context)



class UserUpdateDeleteView(PermissionRequiredMixin,LoginRequiredMixin,View):
    model=User
    template_name='auth/users.html'
    permission_required=''

    def post(self, request, id, *args, **kwargs):
        user=User.objects.get(id=id)
        if id:
            user.username=request.POST['username']
            user.first_name=request.POST['first_name']
            user.last_name=request.POST['last_name']
            user.email=request.POST['email']
            user.is_active = "is_active" in request.POST
            user.is_staff = "is_staff" in request.POST
            user.is_superuser = "is_superuser" in request.POST
            user.save()
            return redirect('users')
        return render (request, self.template_name)

    def get(self, request, id, *args, **kwargs):
        user=User.objects.get(id=id)
        user.delete()
        return redirect('users')

class UserProfileView(View,PermissionRequiredMixin,LoginRequiredMixin):
    permission_required = ''
    template_name = 'user/profile.html'

    def get(self, request, id, *args, **kwargs):
        settings = Settings.objects.first()
        now=timezone.now()
        user_profile = User.objects.get(id=id)
        context={
            'user_profile':user_profile,
            'time':now,
            'day':now.strftime('%A'),
            'month':now.strftime('%B'),
            'settings':settings
        }
        return render(request, self.template_name, context)

class RoleManagement(PermissionRequiredMixin,LoginRequiredMixin,View):
    template_name = 'auth/roles.html'
    permission_required=''


    def get(self, request, *args, **kwargs):
        settings = Settings.objects.first()
        groups = Group.objects.all()
        now=timezone.now()
        messages_data = [{'message': message.message, 'tags': message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)
        context={
            'time':now,
            'day':now.strftime('%A'),
            'second':now.second,
            'minute':now.minute,
            'hour':now.hour,
            'month':now.strftime('%B'),
            'year':now.year,
            'groups':groups,
            'messages_json': messages_json,
            'settings':settings
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            name=request.POST['name']
            Group.objects.get_or_create(name=name)
            messages.success(request, 'Role created successfully')
            return redirect('roles-management')

class UpdateDeleteRole(PermissionRequiredMixin,LoginRequiredMixin,View):
    template_name = 'auth/roles.html'
    permission_required=''


    def post(self, request, id, *args, **kwargs):
            name=request.POST['name']
            Group.objects.filter(id=id).update(name=name)
            messages.success(request, 'Role updated successfully')
            return redirect('roles-management')


    def get(self, request, id, *args, **kwargs):
        Group.objects.get(id=id).delete()
        return redirect('roles-management')

class RolePermission(PermissionRequiredMixin,LoginRequiredMixin,View):
    template_name = 'auth/role-permission.html'
    permission_required=''

    def get(self, request, id,*args, **kwargs):
        settings = Settings.objects.first()
        permissions = Permission.objects.all()
        group=Group.objects.get(id=id)
        now=timezone.now()

        messages_data = [{'message': message.message, 'tags': message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)
        context={
            'time':now,
            'day':now.strftime('%A'),
            'second':now.second,
            'minute':now.minute,
            'hour':now.hour,
            'month':now.strftime('%B'),
            'year':now.year,
            'permissions':permissions,
            'group':group,
            'messages_json': messages_json,
            'settings':settings
        }
        return render(request, self.template_name, context)

    def post(self, request, id, *args, **kwargs):
        group = Group.objects.get(id=id)
        permissions =request.POST.getlist('permission[]')

        group.permissions.clear()

        for permission in permissions:
            permission=Permission.objects.get(id=permission)
            group.permissions.add(permission)

        messages.success(request, 'Permissions updated successfully')
        return redirect('roles-management')

class UserRole(PermissionRequiredMixin, LoginRequiredMixin, View):
    template_name = 'auth/users.html'
    permission_required = ''

    def get(self, request,user_id, *args, **kwargs):
        settings = Settings.objects.first()
        user = get_object_or_404(User, id=user_id)
        groups = Group.objects.all()
        now = timezone.datetime.now()

        messages_data = [{'message': message.message, 'tags': message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)

        context = {
            'time': now,
            'day': now.strftime('%A'),
            'second': now.second,
            'minute': now.minute,
            'hour': now.hour,
            'month': now.strftime('%B'),
            'year': now.year,
            'user': user,
            'groups': groups,
            'messages_json': messages_json,
            'settings':settings
        }
        return render(request, self.template_name, context)

    def post(self, request, user_id, *args, **kwargs):
        user = get_object_or_404(User, id=user_id)
        groups = request.POST.getlist('group')

        user.groups.clear()

        for group in groups:
            group = Group.objects.get(id=group)
            user.groups.add(group)

        messages.success(request, 'Groups updated successfully')
        return redirect('users')

class SettingView(View, LoginRequiredMixin):
    template_name = 'settings/setting.html'

    def get(self, request, *args, **kwargs):
        settings = Settings.objects.first()
        now=timezone.now()
        messages_data = [{'message': message.message, 'tags': message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)

        context={
            'settings':settings,
            'day': now.strftime('%A'),
            'second': now.second,
            'minute': now.minute,
            'hour': now.hour,
            'month': now.strftime('%B'),
            'year': now.year,
            'time':now,
            'messages_json':messages_json
        }
        return render(request, self.template_name, context)


    def post(self, request, *args, **kwargs):
        settings = Settings.objects.first()

        settings.inventory = 'inventory' in request.POST
        settings.human_resources = 'human_resources' in request.POST
        settings.pos = 'pos' in request.POST
        settings.accounting = 'accounting' in request.POST
        settings.authentication = 'authentication' in request.POST
        settings.authorization = 'authorization' in request.POST
        settings.save()

        messages.success(request, 'settings updated successfully')
        return redirect('settings-management')

class ActivateSettingsView(View, LoginRequiredMixin):
    template_name = 'settings/setting.html'

    def post(self, request, *args, **kwargs):
        settings = Settings.objects.first()
        activate = 'active' in request.POST

        if not settings:
            Settings.objects.create(active=activate)
        else:
            settings.active = activate
            settings.save()
        messages.success(request, 'settings activated successfully')
        return redirect('settings-management')



# ServiceManagement

class ServiceManagement(PermissionRequiredMixin, LoginRequiredMixin, View):
    template_name = 'service/management.html'
    permission_required = 'stock.view_category'

    def get(self, request, *args, **kwargs):
        settings = Settings.objects.first()
        services = Service.objects.all()
        now = datetime.now()

        # Serialize messages for the current request
        messages_data = [{'message': message.message, 'tags': message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)

        context = {
            'services': services,
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
            return redirect('service-management')

        if Service.objects.filter(name__in=names).exists():
            messages.error(request, 'One or service with the given names already exist')
            return redirect ('service-management')

        services = []
        for name in names:
            service = Service(name=name,user=request.user)
            services.append(service)

        Service.objects.bulk_create(services)
        messages.success(request, 'Service created successfully')
        return redirect('service-management')

class UpdateDeleteService(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = ""

    def post(self, request, id, *args, **kwargs):
        service = get_object_or_404(Service, id=id)

        names = request.POST.getlist('name[]')
        for i in range(len(names)):

            existing_service = Service.objects.filter(name__in=names).exclude(id=service.id).first()
            if existing_service:
                messages.error(request, 'Service with name already exist')
                return redirect('service-management')

            if i == 0:
                service.name = names[i]
                service.save()
            else:
                new_service = Service(name=names[i])
                new_service.save()
                messages.success(request, 'service updated successfully')
        return redirect('service-management')

    def get(self, request, id, *args, **kwargs):
        Service.objects.get(id=id).delete()
        messages.success(request, 'service deleted successfully')
        return redirect('service-management')

class BulkUpdateService(View, LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = ''

    def post(self, request, *args, **kwargs):
        services = get_list_or_404(Service)

        for s in services:
            updated_service = request.POST.get(f'name_{s.id}')
            existing_service = Service.objects.filter(name=updated_service).exclude(id=s.id).first()
            if existing_service:
                messages.error(request, f'category with id {s.id} already exist')
            s.name = updated_service
        Service.objects.bulk_update(services, ['name'])
        messages.success(request, 'services updated successfully')
        return redirect('service-management')

# ExpensesManagement

class ExpenseManagement(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'expenses/management.html'
    permission_required = ''

    def get(self, request, *args, **kwargs):
        settings = Settings.objects.first()
        expenses=Expenses.objects.annotate(truncated_date=TruncDate('date')).values('date').annotate(total_expense=Sum(
            ExpressionWrapper(F('cost'),output_field=DecimalField()))).order_by('-date')
        services = Service.objects.all()
        now = timezone.datetime.now()
        messages_data = [{'messages': message.message, 'tags': message.tags} for message in messages.get_messages(request)]
        messages_json = json.dumps(messages_data)

        context = {
            'expenses': expenses,
            'time': now,
            'messages_json': messages_json,
            'month': now.strftime('%B'),
            'day': now.strftime('%A'),
            'settings': settings,
            'services': services,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
            services_ids = request.POST.getlist('expenses_name[]')
            costs = request.POST.getlist('cost[]')
            dates = request.POST.getlist('date[]')

            if not (len(services_ids) == len(costs) == len(dates)):
                messages.error(request, 'All fields must have the same number of entries.')
                return redirect('expenses-management')

            if not services_ids:
                messages.info(request, 'No expenses provided.')
                return redirect('expenses-management')

            expenses_to_create = []

            for i in range(len(services_ids)):
                try:
                    service = get_object_or_404(Service, id=services_ids[i])
                    cost = Decimal(costs[i])
                    date = dates[i]

                    expense = Expenses(
                        user=request.user,
                        expenses_name=service,  # Correct field name
                        cost=cost,
                        date=date
                    )

                    expenses_to_create.append(expense)

                except Exception as e:
                    messages.error(request, f"Error in row {i + 1}: {str(e)}")
                    return redirect('expenses-management')

            Expenses.objects.bulk_create(expenses_to_create)

            messages.success(request, 'Expenses added successfully.')
            return redirect('expenses-management')


class UpdateDeleteExpense(View, LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = ''

    def post(self, request, *args, **kwargs):
        expense_ids = request.POST.getlist('expense_id[]')

        for eid in expense_ids:
            expense = get_object_or_404(Expenses, id=eid)

            service_id = request.POST.get(f'expenses_name_{eid}')
            cost = request.POST.get(f'cost_{eid}')
            date_str = request.POST.get(f'date_{eid}')

            if not (service_id and cost and date_str):
                continue

            service = get_object_or_404(Service, id=service_id)

            try:
                expense.cost = Decimal(cost)
                expense.date = datetime.strptime(date_str, '%Y-%m-%d').date()
                expense.expenses_name = service
                expense.save()
            except Exception as e:
                messages.error(request, f"Error updating expense {eid}: {str(e)}")
                continue

        messages.success(request, "Expenses updated successfully.")
        return redirect('expenses-management')
    
    def get(self, request, id, *args, **kwargs):
        # Delete the expense
        expense = get_object_or_404(Expenses, id=id)
        expense.delete()
        messages.success(request, "Expense deleted successfully.")
        return redirect('expenses-management')

class BulkUpdateExpense(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = ''  # add if needed

    def post(self, request, *args, **kwargs):
        expense_ids = request.POST.getlist('expense_id[]')

        for eid in expense_ids:
            service_id = request.POST.get(f'expenses_name_{eid}')
            cost = request.POST.get(f'cost_{eid}')
            date_str = request.POST.get(f'date_{eid}')

            if not (service_id and cost and date_str):
                continue

            service = get_object_or_404(Service, id=service_id)

            try:
                cost_decimal = Decimal(cost)
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            except Exception:
                continue

            if int(eid) > 0:
                # Update existing expense
                expense = get_object_or_404(Expenses, id=eid)
                expense.expenses_name = service
                expense.cost = cost_decimal
                expense.date = date_obj
                expense.save()
            else:
                # Create new expense
                Expenses.objects.create(
                    user=request.user,
                    expenses_name=service,
                    cost=cost_decimal,
                    date=date_obj
                )

        messages.success(request, "Expenses updated successfully.")
        return redirect('expenses-management')

class ViewExpenses(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = 'expenses/view_expense.html'
    permission_required = 'stock.view_purchase'

    def get(self, request, truncated_date, *args, **kwargs):
        settings = Settings.objects.first()
        expenses = Expenses.objects.filter(date=truncated_date)
        services= Service.objects.all()
        now=datetime.now()


        context = {
            'time': now,
            'year': now.year,
            'month': now.strftime('%B'),
            'day': now.strftime('%A'),
            'expenses': expenses,
            'truncated_date': truncated_date,
            'services':services,
            'settings':settings,
        }

        return render(request, self.template_name, context)
   

def expenses_report_pdf(request):
    """
    Generate PDF expenses report filtered by date range and optional service.
    Shows totals per service per date and grand total.
    """
    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        service_id = request.POST.get('service_id')  # optional filter

        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

                # Base queryset
                expenses = Expenses.objects.filter(date__gte=start_date, date__lte=end_date)

                # Filter by service if provided
                if service_id:
                    expenses = expenses.filter(expenses_name_id=service_id)
                    selected_service = get_object_or_404(Service, id=service_id)
                else:
                    selected_service = None

                # Aggregate total per date per service
                daily_service_totals = (
                    expenses
                    .values('date', 'expenses_name__name')
                    .annotate(total=Sum('cost'))
                    .order_by('date', 'expenses_name__name')
                )

                # Grand total
                grand_total = sum([Decimal(s['total']) for s in daily_service_totals]) if daily_service_totals else Decimal('0.00')

                # Context for template
                context = {
                    'start_date': start_date,
                    'end_date': end_date,
                    'selected_service': selected_service,
                    'daily_service_totals': daily_service_totals,
                    'grand_total': grand_total
                }

                # Render HTML template
                html = render_to_string('expenses/report.html', context)

                # Create PDF response
                response = HttpResponse(content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="Expenses_Report.pdf"'

                # Generate PDF
                pisa_status = pisa.CreatePDF(BytesIO(html.encode('UTF-8')), dest=response)
                if pisa_status.err:
                    return HttpResponse(f"Error generating PDF: <pre>{pisa_status.err}</pre>")

                return response

            except ValueError:
                return HttpResponse('Invalid date format. Use YYYY-MM-DD')

    return HttpResponse('No valid date or service was selected')