from django.contrib import admin
from .models import Category, Resource


class ResourceAdmin(admin.ModelAdmin):
    list_filter = ('language', 'r_type', 'categories__name')
    search_fields = ('resource_id', 'title')


admin.site.register(Category)
admin.site.register(Resource, ResourceAdmin)
