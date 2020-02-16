from django.db import models
from django.urls import reverse


# Create your models here.

class Image(models.Model):
    name = models.CharField(max_length=255)
    photo = models.ImageField()
    img_hash = models.CharField(max_length=32, unique=True)

    def get_absolute_url(self):
        return reverse('image', args=[str(self.img_hash)])

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["id"]
