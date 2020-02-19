from django.db import models


class Category(models.Model):
    category_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __unicode__(self):
        return u"{}".format(self.name)


class Resource(models.Model):
    catalog_id = models.CharField(max_length=255)
    resource_id = models.CharField(max_length=255)
    title = models.TextField()
    r_type = models.CharField(max_length=255, null=True, blank=True)
    categories = models.ManyToManyField(Category, related_name='resources')
    language = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        unique_together = ['catalog_id', 'resource_id']

    def __unicode__(self):
        return u"catalog_id - {}, {}".format(self.catalog_id, self.title)



