from django.urls import path
from .views import *
from . import views



urlpatterns = [
    path('dashboard/home', views.Dashboard, name='home'),
    path('', views.login_view, name='login'),
    path('password_reset',views.password_reset,name='password-reset'),
    path('reset/<uidb64>/<token>/', views.custom_password_reset_confirm, name='password_reset_confirm'),
    path('logout/',views.logout_view, name="logout"),
    path('change-password/', ChangePasswordView.as_view(), name='custom_password_change'),


    # userManagement
    path('user/', UserManagement.as_view(), name='users'),
    path('register/user', UserManagement.as_view(), name='register'),
    path('edit/user/<int:id>', UserUpdateDeleteView.as_view(), name='update-user'),
    path('view/user/<int:id>',UserUpdateDeleteView.as_view(), name="view-user"),
    path('delete/user/<int:id>',UserUpdateDeleteView.as_view(), name="delete-user"),
    path('profile/<int:id>', UserProfileView.as_view(), name="user-profile"),
    
    
    # RolesManagement
    path('roles/', RoleManagement.as_view(), name='roles-management'),
    path('update/role/<int:id>', UpdateDeleteRole.as_view(), name='update-role'),
    path('delete/role/<int:id>', UpdateDeleteRole.as_view(), name='delete-role'),
    
    # RolesPermission
    path('role/permission/<int:id>', RolePermission.as_view(), name='role-permission'),
    path('user/role/<int:user_id>/', UserRole.as_view(), name='user-role'),
    
    # SettingsManagement
    path('settings/', SettingView.as_view(), name='settings-management'),
    path("activation/", ActivateSettingsView.as_view(), name="activate-setting"),

    #ServiceManagement 
    path('service/', ServiceManagement.as_view(), name="service-management"),
    path('update/service/<int:id>', UpdateDeleteService.as_view(), name="update-service"),
    path('delete/service/<int:id>', UpdateDeleteService.as_view(), name="delete-service"),
    path('bulk/update/service', BulkUpdateService.as_view(), name='bulk-update-service'),
   



    #ExpensesManagement 
    path('expense/', ExpenseManagement.as_view(), name='expenses-management'),
    path('delete/expense/<int:id>', UpdateDeleteExpense.as_view(), name='delete-expense'),
    path('update/expense/<int:id>', UpdateDeleteExpense.as_view(), name='update-expense'),
    path('bulk/update/expense', BulkUpdateExpense.as_view(), name='bulk-update-expense'),
    path('view/expenses/<str:truncated_date>/',ViewExpenses.as_view(), name='view-expenses'),
    path('expenses/report', views.expenses_report_pdf, name="expenses-repo"),


]