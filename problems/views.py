from django.shortcuts import render
from django.http import JsonResponse
from problems.models import Manufacturer, Device, MDR, DeviceProblem, PatientProblem

from django.db.models import Count

import numpy as np

def list_manufacturers(request):
    context = {}
    
    ms = Manufacturer.objects.all().order_by('name')
    for m in ms:
        devices = m.device_set.all().annotate(count=Count('mdr')).filter(count__gte=1)
        if len(devices) > 0:
            context[m.name] = [{'brand_name':d.brand_name,'generic_name':d.generic_name,'model_number':d.model_number} for d in devices]
    return JsonResponse(context)

def list_devices(request):
    context = {}
    ds = Device.objects.all().order_by('model_number').annotate(count=Count('mdr')).filter(count__gte=1)
    for d in ds:
        ms = np.array(d.manufacturer.all().values_list('name',flat=True))
        context[d.brand_name] = {'brand_name':d.brand_name,'generic_name':d.generic_name,'model_number':d.model_number, 'manufacturers':list(ms)}
    return JsonResponse(context)

def device_info(request, mn):
    context = {}
    device = Device.objects.get(model_number = mn)
    mdrs = MDR.objects.filter(device = device)
    pps = PatientProblem.objects.filter(mdr__device = device)
    dps = DeviceProblem.objects.filter(mdr__device = device)
    
    context['BrandName'] = device.brand_name
    context['GenericName'] = device.generic_name
    n_reports = len(mdrs)
    context['n_reports'] = n_reports

    context['patient_problems'] = {}
    for pp in pps:
        these = mdrs.filter(patient_problem = pp)
        context['patient_problems'][pp.description] = these.__len__()
    context['device_problems'] = {}
    for dp in dps:
        these = mdrs.filter(device_problem = dp)
        context['device_problems'][dp.description] = these.__len__()

    return JsonResponse(context)
        