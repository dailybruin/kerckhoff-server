from django.contrib import admin

from .models import Package, PackageSet


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    pass


@admin.register(PackageSet)
class PackageSetAdmin(admin.ModelAdmin):
    pass
