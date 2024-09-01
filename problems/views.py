from django.shortcuts import render
from django.http import JsonResponse
from problems.models import Manufacturer, Device, MDR, DeviceProblem, PatientProblem
from django.db.models import Count

import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(filename='myapp.log', level=logging.INFO)

def device_info(request, mn):
    logger.info(f'Device Info / {mn}')
    context = {}
    device = Device.objects.get(model_number = mn)
    mdrs = MDR.objects.filter(device = device)
    pps = PatientProblem.objects.filter(mdr__device = device).exclude(description = 'No Clinical Signs, Symptoms or Conditions')
    dps = DeviceProblem.objects.filter(mdr__device = device)
    ###
    context['Manufacturer'] = ', '.join(list(device.manufacturer.all().values_list('name', flat=True)))
    context['BrandName'] = device.brand_name
    context['GenericName'] = device.generic_name
    n_reports = len(mdrs)
    context['n_reports'] = n_reports
    ###
    context['problem_table'] = []
    context['dps'] = []
    for mdr in mdrs:
        for dp in mdr.device_problem.all():
            context['problem_table'].append({'Date':mdr.event_date,'Problem':dp.description, 'Type':'Device', })
    context['pps'] = []
    for mdr in mdrs:
        for pp in mdr.patient_problem.all():
            context['problem_table'].append({'Date':mdr.event_date,'Problem':pp.description, 'Type':'Patient', })
    context['problem_table'] = pd.DataFrame(context['problem_table']).sort_values(by='Date').to_html(index=False)
    ###
    return render(request, 'problems/device_info.html', context)

def device_search(request):
    context = {}
    if request.method == 'POST':
        context['POSTED'] = True
        matches = Device.objects.all().filter(brand_name__contains=request.POST['device_name_search']).order_by('brand_name') | Device.objects.all().filter(generic_name__contains=request.POST['device_name_search']).order_by('brand_name')
        matches = matches & Device.objects.all().filter(manufacturer__name__contains=request.POST['manufacturer_name_search']).order_by('brand_name')
        matches = matches.exclude(model_number__contains="/").distinct()
        matches = matches[:1000] #TODO make pages of results. currently empty searches crash
        mfrs = []
        for m in matches:
            m.mnames = ', '.join(np.sort(m.manufacturer.all().values_list('name',flat=True)))
            mfrs.append(m.mnames)
        mfrs = np.array(mfrs)
        umfrs = np.unique(mfrs)

        context['mmatches'] = {}
        for mfr in umfrs:
            context['mmatches'][mfr] = [matches[int(i)] for i in np.arange(len(matches))[mfrs == mfr]]

        context['current_device_name_search'] = request.POST['device_name_search']
        context['current_manufacturer_name_search'] = request.POST['manufacturer_name_search']

        logger.info(f'Device Search / {request.POST['device_name_search']} / {request.POST['manufacturer_name_search']}')

    return render(request, 'problems/device_search.html', context)