from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from problems.models import Manufacturer, Device, MDR, DeviceProblem, PatientProblem
from django.db.models import Count, F
from django.urls import reverse
from django.contrib.sitemaps import Sitemap

import numpy as np
import pandas as pd
import logging
import plotly.graph_objects as go
import plotly.io as pio
import time
import gc


logger = logging.getLogger(__name__)
logging.basicConfig(filename='myapp.log', level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

def device_info(request, mn):
    logger.info(f'Device Info / {mn}')
    context = {}
    device = Device.objects.get(model_number = mn)
    mdrs = MDR.objects.filter(device = device)
    pps = PatientProblem.objects.filter(mdr__device = device).exclude(description = 'No Clinical Signs, Symptoms or Conditions').annotate(mdr_id = F('mdr')).annotate(date = F('mdr__event_date'))
    dps = DeviceProblem.objects.filter(mdr__device = device).annotate(mdr_id = F('mdr')).annotate(date = F('mdr__event_date'))
    if len(mdrs) > 1000:
        pps = pps.filter(date__gte = pd.to_datetime('1/1/2020'))
        dps = dps.filter(date__gte = pd.to_datetime('1/1/2020'))
    ### general info
    context['Manufacturer'] = ', '.join(list(device.manufacturer.all().values_list('name', flat=True)))
    context['BrandName'] = device.brand_name
    context['GenericName'] = device.generic_name
    n_reports = len(mdrs)
    context['n_reports'] = n_reports
    if len(mdrs)>0:
        context['problem_table'] = []
        if len(pps) > 0:
            pp_df = pd.DataFrame(pps.values())
            pp_df['Year'] = pd.to_datetime(pp_df['date']).dt.to_period('Y')
            pp_df['Description'] = pp_df['description']
            pp_df['Events/year'] = 1
            g = pp_df.groupby(['Year', 'Description'], as_index = False)['Events/year'].count()
            g['Type'] = 'Patient'
            context['problem_table'].append(g)
        if len(dps) > 0:
            dp_df = pd.DataFrame(dps.values())
            dp_df['Year'] = pd.to_datetime(dp_df['date']).dt.to_period('Y')
            dp_df['Description'] = dp_df['description']
            dp_df['Events/year'] = 1
            g = dp_df.groupby(['Year', 'Description'], as_index = False)['Events/year'].count()
            g['Type'] = 'Device'
            context['problem_table'].append(g)
        context['problem_table'] = pd.concat(context['problem_table']).sort_values(by=['Year', 'Type', 'Description'], ascending=False).to_html(index=False)
    ### agg for problem type by year
    if len(mdrs)>4:
        df = pd.DataFrame.from_records(mdrs.values())
        df = df[pd.to_datetime(df.event_date)>pd.to_datetime('1/01/2009')]
        df['mo'] = df['event_date'].to_numpy().astype('datetime64[M]')
        pt = df.pivot_table(columns = 'event_type', index = 'mo', aggfunc='count', fill_value=0).xs('device_id', axis=1, level=0)
        plots = {}
        c = {'Death':'red','Injury':'orange','Malfunction':'purple'}
        p = {'Death':'Deaths','Injury':'Injuries','Malfunction':'Malfunctions'}
        for et in ['Death','Injury','Malfunction']:
            if et not in pt.columns:
                pt[et] = np.zeros(len(pt.index))
            fig = go.Figure()
            fig.add_trace( go.Scatter(
                x=pt.index, y = pt[et],
                mode = 'markers', marker= dict(color=c[et]),
                line = dict(color='black', dash='dot')))
            fig.update_layout(
                title=f'{p[et]} by Month',
                xaxis_title = 'Month',
                yaxis_title = f'{p[et]}',
                template = 'plotly_white',
                width=400, height=400)
            plots[et] = pio.to_html(fig, include_plotlyjs='cdn', full_html=False, default_width='100%', default_height='100%',)
        context['plots'] = plots
    gc.collect()
    return render(request, 'problems/device_info.html', context)

def device_search(request):
    context = {}
    if request.method == 'POST':
        context['POSTED'] = True
        ###
        matches = Device.objects.all().filter(brand_name__contains=request.POST['device_name_search']) | Device.objects.all().filter(generic_name__contains=request.POST['device_name_search'])
        matches = matches & Device.objects.all().filter(manufacturer__name__contains=request.POST['manufacturer_name_search'])
        ###
        matches = matches.annotate(co = Count('manufacturer', distinct = True)).filter(co__lte = 10)
        matches = matches.annotate(coMDR = Count('mdr'))
        matches = matches.exclude(model_number__contains="/").exclude(model_number="*").exclude(model_number="UNKNOWN")
        matches = matches[:1000] #TODO make pages of results. currently empty searches crash
        ###
        mfrs = []
        mfrsCounts = {}
        for m in matches:
            mms = m.manufacturer.all().order_by('name').values_list('name',flat=True)
            if len(mms) > 5:
                m.mnames = ', '.join(mms[:5]) + ' and others'
            else:
                m.mnames = ', '.join(mms)
            mfrs.append(m.mnames)
            mfrsCounts[m.mnames] = (mfrsCounts[m.mnames] + m.coMDR if m.mnames in mfrsCounts.keys() else m.coMDR)
        ###
        mfrs = np.array(mfrs)
        umfrs, mc = np.unique(mfrs, return_counts=True)
        counts = np.array([mfrsCounts[x] for x in umfrs]) / mc
        umfrs = umfrs[np.argsort(-counts)]
        ###
        context['mmatches'] = {}
        for mfr in umfrs:
            context['mmatches'][mfr] = [matches[int(i)] for i in np.arange(len(matches))[mfrs == mfr]]
        ###
        context['current_device_name_search'] = request.POST['device_name_search']
        context['current_manufacturer_name_search'] = request.POST['manufacturer_name_search']
        logger.info(f'Device Search / {request.POST['device_name_search']} / {request.POST['manufacturer_name_search']}')
        gc.collect()
    return render(request, 'problems/device_search.html', context)

def home(request):
    logger.info(f'Homepage')
    context = {}
    return render(request, 'problems/home.html', context)

class DeviceSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.5
    def items(self):
        return Device.objects.exclude(model_number__contains="/").annotate(co = Count('mdr')).order_by('-co')[:49990]
    def location(self, item):
        return reverse('device_info', kwargs={"mn": item.model_number})

class StaticViewSitemap(Sitemap):
    priority = 1
    changefreq = "daily"
    def items(self):
        return ["index", "device_search", "robots.txt"]
    def location(self, item):
        return reverse(item)
    