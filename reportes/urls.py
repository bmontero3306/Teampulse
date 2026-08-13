from django.urls import path

from reportes import views

app_name = "reportes"

urlpatterns = [
    path("iso/", views.IsoPreviewView.as_view(), name="iso"),
    path("iso/pdf/", views.IsoPdfView.as_view(), name="iso_pdf"),
    path("iso/excel/", views.IsoExcelView.as_view(), name="iso_excel"),
]
