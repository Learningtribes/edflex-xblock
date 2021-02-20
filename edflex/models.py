from django.db import models
from django.utils.translation import ugettext_lazy as _


class Category(models.Model):
    category_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    catalog_id = models.CharField(max_length=255, null=True, blank=True)
    catalog_title = models.CharField(max_length=255, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, db_index=True, null=True)
    modified = models.DateTimeField(auto_now=True, db_index=True, null=True)

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __unicode__(self):
        return u"{} - {}".format(self.catalog_title, self.name)


class Resource(models.Model):
    catalog_id = models.CharField(max_length=255)
    resource_id = models.CharField(max_length=255)
    title = models.TextField()
    r_type = models.CharField(max_length=255, null=True, blank=True)
    categories = models.ManyToManyField(Category, related_name='resources')
    language = models.CharField(max_length=255, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, db_index=True, null=True)
    modified = models.DateTimeField(auto_now=True, db_index=True, null=True)

    class Meta:
        unique_together = ['catalog_id', 'resource_id']

    def __unicode__(self):
        return u"catalog_id - {}, {}".format(self.catalog_id, self.title)



