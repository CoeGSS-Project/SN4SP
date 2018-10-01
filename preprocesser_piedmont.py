import platform
import sys
import os
import time
import datetime as dt
import numpy as np
from scipy import linalg as la
import math
import h5py
from mpi4py import MPI
import pandas as pd
import pickle, gzip

r_earth=6.3781*10**6

def GeoDist(lat1, lon1, lat2, lon2):
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)
    
    dlon = lon1 - lon2
    
    y = math.sqrt((math.cos(lat2) * math.sin(dlon)) ** 2+ (math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)) ** 2)
    x = math.sin(lat1) * math.sin(lat2) + math.cos(lat1) * math.cos(lat2) * math.cos(dlon)
    c = math.atan2(y, x)
    return r_earth * c



def preprocessing(comm, size, rank):
    
    if os.getcwd()=='/home/sarawalk/Piedmont/Piedmont_2_0':
        home="/home/sarawalk/Piedmont/Piedmont_2_0/"
        in_file="/vdb1/sarawalk/Piedmont_out/Syn_Pops/synthPop_Piedimont_10pc_2011.h5"
        out_file='/vdb1/sarawalk/Piedmont_out/Syn_Pops/synthPop_Piedimont_10pc_2011_ppd.h5'
        helper='/vdb1/sarawalk/maps_and_rasters/resources/Italy/boundaries/Piemonte_NUTS3_to_LAU2_gdf.pkl.gz'
    else:
        if platform.system()=='Darwin':
            home='/Users/Fabio/'
        else:
            home="/home/fabio/"
        in_file=home+'Documents/Lavoro/Similarity_Networks/synthPop_Piedimont_10pc_2011.h5'
        out_file=home+'Documents/Lavoro/Similarity_Networks/synthPop_Piedimont_10pc_2011_ppd.h5'
        helper=home+'Documents/Lavoro/Similarity_Networks/Piemonte_NUTS3_to_LAU2_gdf.pkl.gz'


    

    with h5py.File(in_file, 'r') as f:
        print '{:%Y-%m-%d %H:%M:%S}'.format(dt.datetime.now())+' starting #'+str(rank)
        sys.stdout.flush()
        
        # l0=0 refers to the Turin county
        turin_hh_area=f['household'][f['household']['l0']==0]
        # l1=0 refers to the Turin municipality. I am selecting households in the Turin municipality
        turin_hh=turin_hh_area[turin_hh_area['l1']==569]['id']
        # I am selecting agents whose households is in the Turin municipality
        selection=np.isin(f['agent']['hh'], turin_hh)
        # where is the exact position in the list of agents
        where_to=np.where(selection)[0]
        
        
        # I am reducing the sample
        #### WHEN EVERYTHING IS FINE, REMOVE THIS BLOCK
        #a=np.arange(len(where_to))
        #np.random.shuffle(a)
        #sel_l=int(np.round(1*len(where_to)/10))
        #sel=list(np.sort(a[:sel_l]))
        #where_to=where_to[sel]
        #### WHEN EVERYTHING IS FINE, REMOVE THIS BLOCK
        
        
        lt=len(f['agent'])
        lr=len(where_to)
        
        print '{:%Y-%m-%d %H:%M:%S}'.format(dt.datetime.now())+' lr='+str(lr)+' #'+str(rank)
        sys.stdout.flush()
        
        # Here I am calculating the efforts per processor
        effort=np.floor(1.*lr/size)*np.ones(size)
        remainder=lr % size
        offset=np.zeros(size, dtype='>i4')
        for i in xrange(size):
            if i<remainder:
                effort[i]+=1
            if i>0:
                offset[i]=offset[i-1]+effort[i-1]

        my_chunk=xrange(int(offset[rank]),int(offset[rank]+effort[rank]))
        print '{:%Y-%m-%d %H:%M:%S}'.format(dt.datetime.now())+' effort='+str(int(effort[rank]))+' #'+str(rank)
        print '{:%Y-%m-%d %H:%M:%S}'.format(dt.datetime.now())+' my_chunk=['+str(my_chunk[0])+', '+str(my_chunk[-1])+'] #'+str(rank)
        sys.stdout.flush()

        # I am reading data and putting them into a buffer


        ags_dataset = f["agent"]
        ags_ids = np.array(ags_dataset["id"])
        ags_hhi = np.array(ags_dataset["hh"])
        ags_wpi = np.array(ags_dataset["wp"])
        ags_sex = np.array(ags_dataset["sex"])
        ags_age = np.array(ags_dataset["age"])
        ags_rol = np.array(ags_dataset["role"])
        ags_edu = np.array(ags_dataset["edu"])
        ags_emp = np.array(ags_dataset["employed"])
        ags_inc = np.array(ags_dataset["income"])
        
        wps_dataset = f["workplace"]
        wps_ids = np.array(wps_dataset["id"])
        wps_lat = np.array(wps_dataset["lat"])
        wps_lon = np.array(wps_dataset["lon"])
        wps_l1  = np.array(wps_dataset["l1"])
        wps_l2  = np.array(wps_dataset["l2"])
        
        hhs_dataset = f["household"]
        hhs_ids = np.array(hhs_dataset["id"])
        hhs_lat = np.array(hhs_dataset["lat"])
        hhs_lon = np.array(hhs_dataset["lon"])
        hhs_l1 = np.array(hhs_dataset["l1"])
        hhs_l2 = np.array(hhs_dataset["l2"])


    # the helper file contains the information about the bounders of the different municipality and the relative codes. This is necessary in order to assign the possible link to the municipality, i.e. in order to assign every agent to a municipality (identified by its code).
    geoDataFrame = pickle.load(gzip.open(helper, "rb"))
    turin=geoDataFrame[2][geoDataFrame[2]['l0']==0]
    print '{:%Y-%m-%d %H:%M:%S}'.format(dt.datetime.now())+' turin.iloc[0][code]='+str(turin.iloc[0]['code'])+' #'+str(rank)
    sys.stdout.flush()


    with h5py.File(out_file, 'w', driver='mpio', comm=comm, libver='latest') as g:
        ppd_g=g.create_group('SPP10pc')
        # pre-processed data
        ppd_da=ppd_g.create_dataset('da', data=np.array(['c', 'o', 'c','c', 'c', 'o','g','g','g','g','o']))

        dtype=np.dtype([('sex','i8'),('age','i8'), ('role','i8'), ('edu','i8'), ('employed','i8'), ('income','i8'), ('wp_lon','f8'), ('wp_lat','f8'), ('hh_lon','f8'), ('hh_lat','f8'), ('wp_hh','i8')])
        # In principle this step could be automatized, but since some of the original entries (like the wp code)
        # are in a non trivial form, it would not in principle deserve the effort, since it should change from
        # synthetic population to syntehtic population.
        ppd=ppd_g.create_dataset('ppd', (lr,), dtype=dtype)
        for i in my_chunk:
            if i % 10000==0:
                print '{:%Y-%m-%d %H:%M:%S}'.format(dt.datetime.now())+' i='+str(i)+' #'+str(rank)
                sys.stdout.flush()
            j=where_to[i]
            assert j<lt, '{:%Y-%m-%d %H:%M:%S}'.format(dt.datetime.now())+' odd index j='+str(j)+' #'+str(rank)
            
            where_hh = hhs_ids==ags_hhi[j]
            
            aux_hh_lon = hhs_lon[where_hh]
            aux_hh_lat = hhs_lat[where_hh]
            aux_hh_l1 = hhs_l1[where_hh][0]
            aux_hh_l2 = hhs_l2[where_hh][0]
            
            
            
            tmp_wp_idx = ags_wpi[j]
            if tmp_wp_idx > 0:
                where_wp = wps_ids == tmp_wp_idx
                aux_wp_lon = wps_lon[where_wp]
                aux_wp_lat = wps_lat[where_wp]
                wp_hh=np.array([GeoDist(aux_hh_lat, aux_hh_lon, aux_wp_lat, aux_wp_lon)])
            else:
                aux_wp_lon = aux_hh_lon
                aux_wp_lat = aux_hh_lat
                wp_hh = np.zeros(1)
            if i==0:
                print '{:%Y-%m-%d %H:%M:%S}'.format(dt.datetime.now())+'int(ags_sex[j])='+str(int(ags_sex[j]))+' # '+str(rank)
                
            #ppd[i]['sex']=int(ags_sex[j])
            #ppd[i]['age']=int(ags_age[j])
            #ppd[i]['edu']=int(ags_edu[j])
            #ppd[i]['role']=int(ags_rol[j])
            #ppd[i]['employed']=int(ags_emp[j])
            #ppd[i]['income']=int(np.round(ags_inc[j]/1000)) 
            #ppd[i]['wp_lon']=aux_wp_lon[0]
            #ppd[i]['wp_lat']=aux_wp_lat[0]
            #ppd[i]['hh_lon']=aux_hh_lon[0]
            #ppd[i]['hh_lat']=aux_hh_lat[0]
            #ppd[i]['wp_hh']=int(np.round(wp_hh/1000))



            ppd[i]=(int(ags_sex[j]), int(ags_age[j]), int(ags_rol[j]), int(ags_edu[j]), int(ags_emp[j]), int(np.round(ags_inc[j]/1000)), aux_wp_lat[0], aux_wp_lon[0], aux_hh_lat[0], aux_hh_lon[0],int(np.round(wp_hh/1000)))

    print '{:%Y-%m-%d %H:%M:%S}'.format(dt.datetime.now())+' just finished #'+str(rank)
    print '{:%Y-%m-%d %H:%M:%S}'.format(dt.datetime.now())+' We all finished #'+str(rank)



    return 0


if __name__ == "__main__":
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    
    preprocessing(comm, size, rank)
