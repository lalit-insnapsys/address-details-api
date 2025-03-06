from django.db import models

class RealEstateTransaction(models.Model):
    date_mutation = models.DateField()
    valeur_fonciere = models.DecimalField(max_digits=12, decimal_places=2)
    adresse_nom_voie = models.CharField(max_length=255)
    type_local = models.CharField(max_length=100)
    surface_reelle_bati = models.FloatField(null=True, blank=True)
    lot1_surface_carrez = models.FloatField(null=True, blank=True)
    nombre_pieces_principales = models.IntegerField(null=True, blank=True)
    surface_terrain = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.adresse_nom_voie} - {self.valeur_fonciere}€"
