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
from django.db.models.functions import TruncMonth,TruncDay
from django.db.models import ExpressionWrapper,F,FloatField,Sum,DecimalField
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


def Dashboard(request):
        settings = Settings.objects.first()
        day_abbr = [calendar.day_abbr[i].upper() for i in range(0, 7)]
        month_abbr = [calendar.month_abbr[i].upper() for i in range(1, 13)]
        now = timezone.now()

        local_tz = pytz.timezone('Africa/Nairobi')
        local_now = now.astimezone(local_tz)
        today=now.date()
        tomorrow=today + timedelta(days=1)

        yesterday=today - timedelta(days=1)

        # Initialize start_date and end_date
        start_date = today
        end_date = today

        if request.method == 'POST':
            # Get the filter date from POST request
            filter_date_str = request.POST.get('filter')

            if filter_date_str:
                try:
                    filter_date = datetime.strptime(filter_date_str, '%Y-%m-%d').date()

                    # Determine if the filter is for today or yesterday
                    if filter_date == today:
                        start_date = today
                        end_date = today
                    elif filter_date == yesterday:
                        start_date = yesterday
                        end_date = yesterday
                    else:
                        # Handle other date ranges if needed
                        start_date = filter_date
                        end_date = filter_date

                except ValueError:
                    # Handle invalid date format
                    pass

        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        start_of_last_week = start_of_week - timedelta(days=7)
        end_of_last_week = start_of_week - timedelta(days=1)

        total_user=User.objects.filter(is_staff=True).count()

        yesterday_order=Order.objects.filter(status='approved',order_date=yesterday).count()

        today_order=Order.objects.filter(status='approved',order_date=today).count()

        if yesterday_order == 0:
            if today_order > 0:
                order_rate = 100
            else:
                order_rate = 0
        else:
            order_rate=((today_order - yesterday_order)/yesterday_order)*100


        total_order = Order.objects.filter(order_date__range=[start_date, end_date]).count()

        total_income=Order.objects.filter(status='approved',approved_date__date__range=[start_date,end_date]).aggregate(
            total_order=Sum(ExpressionWrapper(F('total_price'),output_field=FloatField())))['total_order'] or 0

        yesterday_income=Order.objects.filter(status='approved',approved_date=yesterday).aggregate(
            total_order=Sum(ExpressionWrapper(F('total_price'),output_field=FloatField())))['total_order'] or 0

        today_income=Order.objects.filter(status='approved',approved_date__date__range=[start_date,end_date]).aggregate(
            total_order=Sum(ExpressionWrapper(F('total_price'),output_field=FloatField())))['total_order'] or 0



        if yesterday_income == 0:
            if today_income > 0:
                income_rate = today_income
            else:
                income_rate = 0
        else:
            income_rate=today_income-yesterday_income


        yesterday_purchase = PurchaseOrder.objects.filter(
            status='approved',
            received_date__date=yesterday 
        ).aggregate(
            total_purchase=Sum('total_cost')
        )['total_purchase'] or Decimal('0.0')


        today_purchase = PurchaseOrder.objects.filter(
            status='approved',
            received_date__date=today
        ).aggregate(
            total_purchase=Sum('total_cost')
        )['total_purchase'] or Decimal('0.0')


        if yesterday_purchase == 0:
            if today_purchase :
                purchases_rate = today_purchase
            else:
                purchases_rate = 0
        else:
            purchases_rate= today_purchase - yesterday_purchase


        monthly_purchase = (
            PurchaseItem.objects
            .filter(purchase_order__received_date__isnull=False)  
            .annotate(month=TruncMonth('purchase_order__received_date'))
            .values('month')
            .annotate(month_total=Sum('price'))
            .order_by('month')
        )



        monthly_sales = Order.objects.filter(status='approved').annotate(
            month=TruncMonth('approved_date')
        ).values('month').annotate(
            month_total=Sum(ExpressionWrapper(F('total_price'), output_field=FloatField()))
        ).order_by('month')



# ProfitMargin
        ps = Order.objects.filter(status='approved').annotate(
            month=TruncMonth('approved_date')
        ).aggregate(
            tps=Sum(ExpressionWrapper(F('total_price'), output_field=DecimalField()))
        )['tps'] or Decimal('0.0')

        sp = PurchaseItem.objects.filter(purchase_order__received_date__isnull=False).annotate(
            month=TruncMonth('purchase_order__received_date')
        ).aggregate(
            spt=Sum('price')
        )['spt'] or Decimal('0.0')

        p = ps - sp  


        purchases = PurchaseOrder.objects.filter(
            status='approved',
            received_date__isnull=False,
            received_date__date__range=[start_date, end_date]
        ).aggregate(
            total_purchase=Sum('total_cost')
        )['total_purchase'] or Decimal('0.0')


        day_sales = Order.objects.filter(
            status='approved',
            approved_date__range=[start_of_last_week, end_of_week]
        ).annotate(day=TruncDay('approved_date')).values('day').annotate(
            day_total=Sum(ExpressionWrapper(F('total_price'), output_field=FloatField()))
        )

        this_week_data = defaultdict(float)
        last_week_data = defaultdict(float)

        for sale in day_sales:
            day = sale['day'].date()  # Fix: convert to date
            total = sale['day_total']
            if start_of_week <= day <= end_of_week:
                day_index = (day - start_of_week).days
                this_week_data[day_abbr[day_index]] = total
            elif start_of_last_week <= day <= end_of_last_week:
                day_index = (day - start_of_last_week).days
                last_week_data[day_abbr[day_index]] = total

        # Prepare labels and datasets for Chart.js
        day_sales = day_abbr
        this_week_totals = [this_week_data.get(day, 0) for day in day_sales]
        last_week_totals = [last_week_data.get(day, 0) for day in day_sales]

        # Aggregate monthly purchases

        purchases_totals = defaultdict(float)
        sales_totals = defaultdict(float)

        for item in monthly_purchase:
            month_index = item['month'].month - 1
            purchases_totals[month_abbr[month_index]] += float(item['month_total'] or 0)

        for item in monthly_sales:
            month_index = item['month'].month - 1
            sales_totals[month_abbr[month_index]] += float(item['month_total'] or 0)


        months = month_abbr
        purchase_totals_list = [purchases_totals[month] for month in months]
        sales_totals_list = [sales_totals[month] for month in months]




        context = {
            'order_rate':order_rate,
            'purchase_totals': json.dumps(purchase_totals_list),
            'sales_totals': json.dumps(sales_totals_list),
            'months': json.dumps(months),
            'this_week_totals': json.dumps(this_week_totals),
            'last_week_totals': json.dumps(last_week_totals),
            'day_sales': json.dumps(day_sales),
            'time': local_now,
            'day': now.strftime('%A'),
            'second': now.second,
            'minute': now.minute,
            'hour': now.hour,
            'month': now.strftime('%B'),
            'year': now.year,
            'purchases': purchases,
            'total_user':total_user,
            'total_income':total_income,
            'p':p,
            'total_order':total_order,
            'filter':start_date,
            'start_date':start_date,
            'end_date':end_date,
            'income_rate':income_rate,
            'settings':settings
        }
        return render(request, 'dashboard/home.html', context)



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
        now=timezone.datetime.now()
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
        now=timezone.datetime.now()
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
        now=timezone.datetime.now()

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
        now=timezone.datetime.now()
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

