from django.contrib import admin

from .models import Package, PackageSet, PackageVersion, PackageItem


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    pass


@admin.register(PackageSet)
class PackageSetAdmin(admin.ModelAdmin):
    pass


@admin.register(PackageVersion)
class PackageVersionAdmin(admin.ModelAdmin):
    pass


@admin.register(PackageItem)
class PackageItemAdmin(admin.ModelAdmin):
    pass
