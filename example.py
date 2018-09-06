# -*- coding: utf-8 -*-
"""
Created on Tue Aug 21 17:27:17 2018

@author: smrak
"""

from pyGnss import pyGnss
from pyGnss import gnssUtils as gu
import georinex as gr
import xarray
from pandas import Timestamp
from datetime import datetime, timedelta
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

f1 = 1575420000
f2 = 1227600000
f5 = 1176450000
c0 = 299792458
###############################################################################
# Plots
def _plot(x,y,title=''):
    plt.figure()
    plt.title(title)
    plt.plot(x,y,'b')
    
def _plotOneParam(t,y,c='b',lli=None,xlim=None,ylim=None,title='',
                  xlabel='',ylabel='',ygrid=False,xgrid=False,
                  figsize=(8,5),formatter='%H:%M:%S'):
    fig = plt.figure(figsize=figsize)
    plt.title(title)
    ax = fig.add_subplot(111)
    date_formatter = DateFormatter(formatter)
    ax.plot(t,y,c)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.tick_params(direction='in')
    if xlim is not None:
        ax.set_xlim(xlim)
    if ylim is not None:
        ax.set_ylim(ylim)
    if ygrid:
        ax.yaxis.grid(linestyle='--')
    if xgrid:
        ax.xaxis.grid(linestyle='--')
    ax.xaxis.set_major_formatter(date_formatter)
    
    return fig
    
def _plotHilbert(t,y,envelope,phase=None,frequency=None,xlim=None, ylim1=None,
                 figsize=(8,5),title='',c='b',formatter='%H:%M:%S'):
    fig = plt.figure(figsize=figsize)
    ax1 = fig.add_subplot(311)
    ax1.set_title(title)
    date_formatter = DateFormatter(formatter)
    ax1.plot(t,y,c)
    ax1.plot(t,envelope, 'r')
    plt.setp(ax1.get_xticklabels(), visible=False)
    ax2 = fig.add_subplot(312, sharex=ax1)
    ax2.plot(t,phase,c)
    plt.setp(ax2.get_xticklabels(), visible=False)
    ax3 = fig.add_subplot(313, sharex=ax1)
    ax3.plot(t[1:],frequency,c)
    if xlim is not None:
        plt.xlim(xlim)
    ax1.tick_params(direction='in')
    ax3.xaxis.set_major_formatter(date_formatter)
    
    return fig
    
def _plotDuo(t,y1,y2,ylim1=None,ylim2=None,xlim=None,title='',figsize=(8,5),
             xlabel='',ylabel1='',ylabel2='',y1ticks=None,y2ticks=None,
             c1='b',c2='k',lw1=1,lw2=1,
             formatter='%H:%M:%S'):
    date_formatter = DateFormatter(formatter)
    fig = plt.figure(figsize=figsize)
    ax1 = fig.add_subplot(111)
    ax1.plot(t,y1,c1,lw=lw1)
    ax2 = ax1.twinx()
    ax2.plot(t,y2,c2,lw=lw2)
    # Labels
    ax1.set_title(title)
    ax1.set_xlabel(xlabel)
    ax1.set_ylabel(ylabel1)
    ax2.set_ylabel(ylabel2)
    if ylim1 is not None:
        ax1.set_ylim(ylim1)
    if ylim2 is not None:
        ax2.set_ylim(ylim2)
    if xlim is not None:
        ax1.set_xlim(xlim)
    if y2ticks is not None:
        ax2.set_yticks(y2ticks)
    ax1.tick_params(direction='in')
    ax2.tick_params(direction='in')
    ax1.xaxis.set_major_formatter(date_formatter)
    
    return fig
    
def _plotEnvelope(t,y1,y2,title='',xlim=None,ylim=None,figsize=(8,5),
                  xlabel='',ylabel='',c1='b',c2='r',formatter='%H:%M:%S',
                  xgrid=False,ygrid=False):
    date_formatter = DateFormatter(formatter)
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111)
    ax.plot(t,y1,c1)
    ax.plot(t,y2,c2, lw=2)
    if ylim is not None:
        ax.set_ylim(ylim)
    if xlim is not None:
        ax.set_xlim(xlim)
    
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    
    if ygrid:
        ax.yaxis.grid(linestyle='--')
    if xgrid:
        ax.xaxis.grid(linestyle='--')
    
    ax.tick_params(direction='in')
    ax.xaxis.set_major_formatter(date_formatter)
    
    return fig
    
###############################################################################
def singleRx(obs, nav, sv='G23', args=['L1','S1'], tlim=None,rawplot=False,
             sp=True,s4=False,polyfit=False,indicator=False,
             alt=300,el_mask=30,skip=20,porder=8,tec_ch=2,
             forder=5,fc=0.1,fs=1):
    
    D = xarray.open_dataset(obs, group='OBS')
    rx_xyz = D.position
    leap_seconds = gu.getLeapSeconds(nav)
    obstimes64 = D.time.values
    times = np.array([Timestamp(t).to_pydatetime() for t in obstimes64]) - timedelta(seconds = leap_seconds)
    #define tlim ie. skip
    if tlim is not None:
        s = ((times>=tlim[0]) & (times<=tlim[1]))
    else:
        s = np.full(times.shape[0], True, dtype=bool)
        s[:skip] = False
    times = times[s]
    
    aer = pyGnss.getSatellitePosition(rx_xyz, sv, times, nav, cs='aer',dtype='georinex')
    # Elevation mask
    idel = aer[1] >= el_mask
    times = times[idel]
    # times to output dict: Y
    Y = {'times': times}
    Y['rx_xyz'] = rx_xyz
    Y['az'] = aer[0][idel]
    Y['el'] = aer[1][idel]
    for arg in args:
        if not arg[1:] == 'TEC':
            X = D.sel(sv=sv)[arg].values[s][idel]
            # To dict
            Y[arg] = X
            # Indicators?
            if indicator:
                try:
                    if arg[0] == 'L' and arg[-1] != '5':
                        argi = arg + 'lli'
                    elif arg[0] == 'C' or arg[0] == 'P' or arg == 'L5':
                        argi = arg + 'ssi'
                    else:
                        argi = ''
                    Xi = D.sel(sv=sv)[argi].values[s:][idel]
                    Y[argi] = Xi
                except Exception as e:
                    print (e)
            if rawplot:
                _plot(times,X,arg)
        if arg[0] == 'L' or arg[0] == 'C':
            if arg == 'C1':
                X = X * f1 / c0 # To cycles
            Xd = pyGnss.phaseDetrend(X, order=porder)
                
            if polyfit:
                # To dict
                Y[arg+'polyfit'] = Xd
            if rawplot:
                if rawplot:
                    _plot(times,Xd,arg+'_detrend_poly')
            if sp:
                Xy = gu.hpf(Xd, order=forder,fc=fc,plot=False,fs=fs)
                # To dict
                Y['sp'] = Xy
                if rawplot:
                    _plot(times[100:],Xy[100:],arg+'_scint')
        if arg[0] == 'S':
            if s4:
                Xy = pyGnss.AmplitudeScintillationIndex(X,60)
                # To dict
                Y['s4'] = Xy
                if rawplot:
                    _plot(times,Xy,arg+'_S4')
                    
        if arg[1:] == 'TEC':
            if tec_ch == 2:
                C1 = D.sel(sv=sv)['C1'].values[s][idel]
                L1 = D.sel(sv=sv)['L1'].values[s][idel]
                C2 = D.sel(sv=sv)['P2'].values[s][idel]
                L2 = D.sel(sv=sv)['L2'].values[s][idel]
            elif tec_ch == 5:
                C1 = D.sel(sv=sv)['C1'].values[s][idel]
                L1 = D.sel(sv=sv)['L1'].values[s][idel]
                C2 = D.sel(sv=sv)['C5'].values[s][idel]
                L2 = D.sel(sv=sv)['L5'].values[s][idel]
            sTEC = pyGnss.getPhaseCorrTEC(L1, L2, C1, C2,channel=tec_ch)
            sTEC = sTEC - np.nanmin(sTEC)
            if arg == 'sTEC':
                # To dict
                Y[arg] = sTEC
                if rawplot:
                    _plot(times, sTEC,title=arg)
            elif arg == 'vTEC':
                vTEC = pyGnss.getVerticalTEC(sTEC,aer[1][idel],alt)
                # To dict
                Y[arg] = vTEC
                if rawplot:
                    _plot(times, vTEC, title=arg)
    return Y

def returnHT(x, fs=1):
    from scipy.signal import hilbert
    analytic_signal = hilbert(x)
    amplitude_envelope = np.abs(analytic_signal)
    instantaneous_phase = np.unwrap(np.angle(analytic_signal))
    instantaneous_frequency = (np.diff(instantaneous_phase) /
                               (2.0*np.pi) * fs)
    return amplitude_envelope, instantaneous_phase, instantaneous_frequency

def mahali(fnc,fnav,sv='G09',args = ['C1', 'L1', 'S1', 'L5', 'vTEC'],tlim=None):
    
    # Obs
    data = singleRx(fnc, fnav, args=args, sv=sv,
                    porder=12, forder=5,fc=0.1,tlim=tlim,
                    s4=False, rawplot=False,tec_ch=2,
                    indicator=False,polyfit=True)
    dt = data['times']
    
    return data, dt

save = 'C:\\Users\\smrak\\Google Drive\\BU\\Projects\\imprint\\figures\\raw\\'
#save = ''
ft = 'MOAT_glitch_L1C1'
#ft = 'mag6_phase_scint'
#tlim = [datetime(2015,10,7,6,10,0), datetime(2015,10,7,6,45,0)]
#tlim = [datetime(2017,8,21,15,0,0), datetime(2017,8,21,22,0,0)]
tlim = None
folder = 'E:\\mahali\\2015-10-07\\'
nc = 'nc\\mah92800.15o.nc'
nav = 'brdc2800.15n'
# MO
folder = 'E:\\mo\\'
nc = 'MOJC2330.17o.nc' #MOAT
nav= 'MOJC2330.17n'
nc = 'MOAT2330.17o.nc'
# Ublox
#folder = 'E:\\ublox\\'
#nc = 'ub_homet3.18o.nc'
#nav= 'brdc2420.18n'
fnc = folder + nc
fnav = folder + nav
data, dt = mahali(fnc=fnc,fnav=fnav,sv='G12',args=['C1', 'L1', 'vTEC'], tlim=tlim)

#xlim = [datetime(2015,10,7,6,10,0), datetime(2015,10,7,6,35,0)]
xlim = [datetime(2017,8,21,17,10,0), datetime(2017,8,21,18,0,0)]
ylim = [-3.14*8, 3.14*15]
ylim = [-3.14, 3.14]
y = 2*np.pi*data['sp']
title = nc
ylabel = 'Scint [rad]'
_plotOneParam(dt,y,c='b',title=title,xlim=xlim,ylabel=ylabel,
              ylim=ylim,ygrid=True,formatter='%H:%M')

title = 'Polyfit'
ylabel = 'L1 phase [cycle]'
_plotOneParam(dt,f1/c0*data['C1polyfit'],ylabel=ylabel,xlim=xlim,ygrid=True,formatter='%H:%M')

ylabel = 'dTEC from dL1'
dTEC = pyGnss.retreiveDTECfromPhase(data['L1polyfit'],f=f1,units='cycle')
_plotOneParam(dt, dTEC,ylabel=ylabel,xlim=xlim,ygrid=True,formatter='%H:%M')
#_plotOneParam(dt,data['L1polyfit'],ylabel=ylabel,xlim=xlim,ygrid=True,formatter='%H:%M')


ylabel = 'TEC [TECu]'
_plotOneParam(dt, data['vTEC'], ylabel=ylabel,xlim=xlim,ygrid=True,formatter='%H:%M')

sfTEC = 0.5 * pyGnss.singleFrequencyTEC(data['L1'], data['C1'], el=data['el'],vertical=True)
ylabel = 'sfTEC'
_plotOneParam(dt, sfTEC, ylabel=ylabel,xlim=xlim,ygrid=True,formatter='%H:%M')
#
#title= 'Hilbert'
envelope, phi, freq = returnHT(y)
#_plotHilbert(dt,y,envelope,phi,frequency=abs(freq), xlim=xlim, title=title,formatter='%H:%M')
#
title = nc
ylabel1 = 'L1-pL1fit = dL1 [rad]'
ylabel2 = 'L1scint [rad]'
xlabel = 'Time [UTC]'
y1 = 2 * np.pi * data['L1polyfit']
y2 = 2 * np.pi * data['sp']
ylim1 = [np.nanmin(y1)+0.1*np.nanmin(y1), np.nanmax(y1)+0.1*np.nanmax(y1)]
ylim2 = [np.nanmin(y2)+0.1*np.nanmin(y1), np.nanmax(y2)+0.1*np.nanmax(y1)]
ylim2 = [-200,25]
y2ticks = [-50,-25,0,25,50]
#y2ticks = [-25,0,25]
_plotDuo(dt,y1,y2,xlim=xlim,ylim1=ylim1,ylim2=ylim2,
         title=title,xlabel=xlabel,ylabel1=ylabel1,ylabel2=ylabel2,
         y2ticks=y2ticks,
         c1='--b',c2='-k',formatter='%H:%M')

############# Compare TECs, dual freq and single freq retreival ###############
title = 'Campare both TECs'
ylabel1 = '(standard) TEC [TECu]'
ylabel2 = '(single freq) TEC [TECu]'
xlabel = 'Time [UTC]'
y1 = data['vTEC']
#y2 = sfTEC
tecdiff = np.nanmean(y1)-np.nanmean(sfTEC)
y2 = sfTEC + tecdiff
ylim1 = [np.nanmin(y1)+0.5*np.nanmin(y1), np.nanmax(y1)+0.1*np.nanmax(y1)]
ylim1 = [-2, 8]
ylim2 = ylim1
_plotDuo(dt,y2,y1,xlim=xlim,ylim1=ylim1,ylim2=ylim2,
         title=title,xlabel=xlabel,ylabel1=ylabel1,ylabel2=ylabel2,
         c1='r',c2='b',formatter='%H:%M',lw1=1,lw2=2)
################################ C and L ######################################
y2 = data['L1polyfit']
y1 = data['C1polyfit']
ylabel1 = 'C1 [cycle]'
ylabel2 = 'L1 [cycle]'
ylim1 = [np.nanmin(y1)+0.1*np.nanmin(y1), np.nanmax(y1)+0.1*np.nanmax(y1)]
ylim2=ylim1
f = _plotDuo(dt,y1,y2,xlim=xlim,ylim1=ylim1,ylim2=ylim2,
         title=title,xlabel=xlabel,ylabel1=ylabel1,ylabel2=ylabel2,
         c1='r',c2='b',formatter='%H:%M',lw1=1,lw2=2)
###############################################################################
if save is not None and save is not '':
    save = save + ft + '.png'
    f.savefig(save, dpi=300)
###############################################################################
    
#C1hpf = gu.hpf(f1 / c0 * data['C1polyfit'], order=5,fc=0.01,plot=False,fs=1)
#L1hpf = gu.hpf(data['L1polyfit'], order=5,fc=0.01,plot=False,fs=1)
#plt.figure(figsize=(8,6))
#plt.plot(dt,data['C1polyfit'], 'b')
#plt.plot(dt,data['L1polyfit'], 'r')
#plt.xlim(xlim)
#
#plt.figure(figsize=(8,6))
#plt.plot(dt,C1hpf, 'b')
#plt.xlim(xlim)
#
#plt.figure(figsize=(8,6))
#plt.plot(dt,L1hpf, 'b')
#plt.xlim(xlim)
#
#plt.figure(figsize=(8,6))
#plt.plot(dt,C1hpf, 'b')
#plt.plot(dt,L1hpf, 'r')
#plt.xlim(xlim)
#
#plt.figure(figsize=(8,6))
#plt.plot(dt,L1hpf-C1hpf, 'b')
#plt.xlim(xlim)
#
#envelope, phi, freq = returnHT(L1hpf-C1hpf)
#_plotHilbert(dt,L1hpf-C1hpf,envelope,phi,frequency=abs(freq), xlim=xlim, 
#             title=title,formatter='%H:%M')


#xlim = [datetime(2015,10,7,6,15,0), datetime(2015,10,7,6,30,0)]
#_plotEnvelope(dt,y2,envelope,xlim=xlim,ylabel=ylabel2,xlabel=xlabel,
#              ygrid=True,formatter='%H:%M')

# =============================================================================
# # NAV
# aer1 = pyGnss.getSatellitePosition(data['rx_xyz'], int(sv[1:]), dt, fnav, cs='aer')
# plt.figure()
# plt.plot(dt,aer1[1])
# # NAV2
# aer2 = getSatellitePosition(data['rx_xyz'], sv, dt, fnav, cs='aer')
# plt.figure()
# plt.plot(dt,aer2[1])
# navdata = pyGnss.getSatellitePosition(data['rx_xyz'], 9, dt, fnav, navdict=1)
# =============================================================================


## Georinex
#if not 'data' in vars():
#    data = gr.load(mahfolder+obs)
#L1 = data['L1'].sel(sv='G23')