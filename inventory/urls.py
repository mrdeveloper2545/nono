from django.urls import path, include
from . import views
from .views import *


urlpatterns = [
    
    # UnitManagement
    path('unit/', UnitManagement.as_view(), name="unit-management"),
    path('update/unit/<int:id>', UpdateDeleteUnit.as_view(), name="update-unit"),
    path('delete/unit/<int:id>', UpdateDeleteUnit.as_view(), name="delete-unit"),
    path('bulk/unit/update', BulkUpdateUnit.as_view(), name='bulk-update-unit'),

    # CategoryManagement
    path('category/', CategoryManagement.as_view(), name="category-management"),
    path('update/category/<int:id>', UpdateDeleteCategory.as_view(), name="update-category"),
    path('delete/category/<int:id>', UpdateDeleteCategory.as_view(), name="delete-category"),
    path('bulk/update/category', BulkUpdateCategory.as_view(), name='bulk-update-category'),
    

    # MaterialManagement
    path('material/', MaterialManagement.as_view(), name='material-management'),
    path('delete/material/<int:id>', UpdateDeleteMaterial.as_view(), name='delete-material'),
    path('update/material/<int:id>', UpdateDeleteMaterial.as_view(), name='update-material'),
    path('bulk/update/material', BulkUpdateMaterial.as_view(), name='bulk-update-material'),
    

    # VendorManagement
    path('vendors/', VendorManagement.as_view(), name='vendor-management'),
    path("bulk-update/", BulkUpdateVendors.as_view(), name="bulk-vendor-update"),
    path("update/vendor/<int:id>", UpdateDeleteVendor.as_view(), name="update-vendor"),
    path("delete/vendor/<int:id>", UpdateDeleteVendor.as_view(), name="delete-vendor"),

    # PurchaseManagement
    path('purchase/', PurchaseManagementView.as_view(), name='purchase-management'),
    path('purchase/<int:pk>/update/', UpdateDeletePurchaseOrderView.as_view(), name='purchase-update'),
    path('purchase/<int:pk>/delete/', UpdateDeletePurchaseOrderView.as_view(), name='purchase-delete'),
    path('purchase/detail/<int:id>/', PurchaseOrderDetailView.as_view(), name='detail-purchase'),
    path('purchase/receive/order/<int:id>/', ReceivePurchaseOrder.as_view(), name='purchase-order-receive'),
    path('purchase/cancell/order/<int:id>/', CancellPurchaseOrder.as_view(), name='purchase-order-cancel'),
    path('purchase/order/invoice/<int:id>/', SinglePurchaseReport.as_view(), name='purchase-invoice'),
    path('pending/', PendingPurchaseOrder.as_view(), name='pending-purchase-order'),
    path('Approve/', ApprovePurchaseOrder.as_view(), name='approve-purchase-order'),
    path('approved/',approvedPurchaseOrderItems.as_view(), name='approved_items'),
    path('cancelled/',cancelledPurchaseOrderItems.as_view(), name='cancelled_items'),
    path('purchase/report', PurchaseReport.as_view(), name='purchase-report-management'),


    # ProductManagement
    path('products/', ProductManagement.as_view(), name="product-management"),
    path('update/product/<int:id>/', UpdateDeleteProduct.as_view(), name="update-product"),
    path('delete/product/<int:id>/', UpdateDeleteProduct.as_view(), name="delete-product"),

    # OrderManagemet
    path('order/', OrderManagementView.as_view(), name='order-management'),
    path('order/approved/<int:id>/', ApproveOrderManagementView.as_view(), name='order-approved'),
    path('order/cancelled/<int:id>/', CancellOrderManagementView.as_view(), name='order-cancelled'),
    path('order/detail/<int:id>/', OrderViewDetail.as_view(), name='order-detail'),
    path('order/delete/<int:pk>/', UpdateDeleteOrder.as_view(), name='delete-order'),
    path('order/update/<int:pk>/', UpdateDeleteOrder.as_view(), name='update-order'),
    path('order/invoice/<int:id>/', SingleOrderReport.as_view(), name='order-invoice'),
    path('order/report', OrderReport.as_view(), name='order-report-management'),




    path('reports/financial/', FinancialReportView.as_view(), name='financial_report'),
    path('unsold-stock-report/', UnsoldStockReportView.as_view(), name='unsold_stock_report'),

]
