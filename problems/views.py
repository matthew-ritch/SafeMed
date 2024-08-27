from django.shortcuts import render
from django.http import JsonResponse
from problems.models import Manufacturer, Device, MDR, DeviceProblem, PatientProblem

import numpy as np

def list_devices_by_manufacturer(request):
    context = {}
    
    ms = Manufacturer.objects.all()
    for m in ms:
        devices = np.array(m.device_set.all().values_list('generic_name',flat=True)).astype(str) + ' XXX ' + np.array(m.device_set.all().values_list('brand_name',flat=True)).astype(str)
        context[m.name] = list(devices)
    # ds = Device.objects.all()
    # for d in ds:
    #     ms = np.array(d.manufacturer.all().values_list('name',flat=True)) # + ' XXX ' + np.array(d.manufacturer.all().values_list('name',flat=True))
    #     context[d.brand_name] = list(ms)

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
        