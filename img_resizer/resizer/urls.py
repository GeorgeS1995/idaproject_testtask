"""img_resizer URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from .views import ImageList,ImageDetail, ImageUploadView
from django.views.decorators.cache import cache_page

urlpatterns = [
    path('', ImageList.as_view(), name='main'),
    path('upload/', ImageUploadView.as_view(), name='img_upload'),
    path('<str:img_hash>/', cache_page(60 * 15)(ImageDetail.as_view()), name='image'),
]
