from django.db import models


class FuelStation(models.Model):
    opis_id = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=2)
    price = models.FloatField()
    lat = models.FloatField()
    lng = models.FloatField()

    class Meta:
        indexes = [
            models.Index(fields=['lat', 'lng'], name='station_lat_lng_idx'),
        ]

    def __str__(self):
        return f'{self.name} ({self.city}, {self.state})'
