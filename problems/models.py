from django.db import models

class Manufacturer(models.Model):
    name = models.CharField( 
         primary_key = True,
         max_length=200) 
    
class Device(models.Model):
    model_number = models.CharField( 
         primary_key = True,
         max_length=200) 
    brand_name = models.CharField(
        max_length=200)
    generic_name = models.CharField(
        max_length=200)
    manufacturer = models.ManyToManyField(Manufacturer)

class PatientProblem(models.Model):
    code = models.IntegerField(primary_key=True)
    description = models.CharField(max_length=200)

class DeviceProblem(models.Model):
    code = models.IntegerField(primary_key=True)
    description = models.CharField(max_length=200)

class MDR(models.Model):
    mdr_report_key = models.IntegerField(primary_key=True)
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    patient_problem = models.ManyToManyField(PatientProblem)
    device_problem = models.ManyToManyField(DeviceProblem)
    event_date = models.DateField()