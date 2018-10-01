"""
    .. module:: piedmont
    :platform: Unix, Windows
    :synopsis: Similarity Network 4 Synthetic Population : Network reconstruction with Lin similarity
    """
import logging

import platform
import sys
import os
import time
import datetime as dt
import matplotlib.pyplot as plt
import pandas as pd
import numpy
import numpy as np
from scipy import linalg as la
import math
import h5py
from mpi4py import MPI
import argparse
import psutil
import getpass

source=MPI.ANY_SOURCE
GLOBAL_SIM_TH=10**-6
r_earth=6.3781*10**6    # Earth radius in meters

# ----------------------------------------------------------------------------------------
# Interface routines
# ----------------------------------------------------------------------------------------
def get_home():
    if os.getcwd()=='/home/sarawalk/Piedmont/Piedmont_2_0':
        home="/home/sarawalk/Piedmont/Piedmont_2_0/"
    elif getpass.getuser().lower() == 'fabio':
        if platform.system()=='Darwin':
            home='/Users/Fabio/'
        else:
            home="/home/fabio/"
    else:
        home=os.getcwd()
    return home

def get_parser():
    """ Get the argument from the command line.
        The defaul arguments put the output of the routine in the proper folder
        (the extra volume added by Marcin),
        uses exponential damping and uses half-length scale set to 5 km.
        """
    
    parser = argparse.ArgumentParser(description="Similarity Network 4 Synthetic Population calculator")
    parser.add_argument("-out",
                        "--out_path",
                        dest="o_path",
                        help="Output Data Directory",
                        default=os.getcwd())
                        parser.add_argument("-in",
                                            "--in_path",
                                            dest="i_path",
                                            help="Input Data Directory",
                                            default=get_home())
                        parser.add_argument("-hss",
                                            "--half_sim_scale",
                                            dest="hss",
                                            help="Half-similarity Scale",
                                            default='5000')
                        parser.add_argument("-d",
                                            "--damping",
                                            dest="damp",
                                            help="Damping Function",
                                            default=0)
                        parser.add_argument("-s",
                                            "--sampling",
                                            dest="sam_p",
                                            help="Percentage of the sample for the similarity calculation",
                                            default=0.1)
                        
    return parser

def preprocessing(home):
    """ Preprocessing (honestly, it is just where to find files)
        """
    with h5py.File(os.path.join(home, 'synthPop_Piedimont_10pc_2011_ppd.h5'), 'r') as f:
        ppd=numpy.array(f['SPP10pc'].get('ppd'))
        da=numpy.array(f['SPP10pc'].get('da'))
        ff=numpy.array(ppd.dtype.names)
    
    #print '{:%Y-%m-%d %H:%M:%S}'.format(dt.datetime.now())+' ff='+str(ff)
    #sys.stdout.flush()
    
    return ppd, da, ff

# ----------------------------------------------------------------------------------------
#        geographic routines
# ----------------------------------------------------------------------------------------

def GeoDist(lat1, lon1, lat2, lon2):
    """ Calculate the geographical distance between two points.
        """
    
    lat1 = numpy.radians(lat1)
    lon1 = numpy.radians(lon1)
    lat2 = numpy.radians(lat2)
    lon2 = numpy.radians(lon2)
    
    dlon = lon1 - lon2
    
    y = numpy.sqrt((numpy.cos(lat2) * numpy.sin(dlon)) ** 2 + (numpy.cos(lat1) * numpy.sin(lat2) - numpy.sin(lat1) * numpy.cos(lat2) * numpy.cos(dlon)) ** 2)
    x = numpy.sin(lat1) * numpy.sin(lat2) + numpy.cos(lat1) * numpy.cos(lat2) * numpy.cos(dlon)
    c = numpy.arctan2(y, x)
    return r_earth * c

def GeoSim(hss_0, pow_law_exp, lat1, lon1, lat2, lon2):
    """ In order to make the Similarity adimensional I have to add a scale to the game.
        This scale is hss, i.e. the scale after which the similairty is damped by a factor 2.
        
        :param pow_law_exp: is the exponent of the power law.
        """
    return (1.*hss_0/(hss_0+GeoDist(lat1, lon1, lat2, lon2)))**pow_law_exp

def GeoExpDamp(hss_0, lat1, lon1, lat2, lon2):
    """
        :param hss_0: works as in the routine before
        """
    return 2**(-GeoDist(lat1, lon1, lat2, lon2)/hss_0)

# ----------------------------------------------------------------------------------------
#        Lin similarity
# ----------------------------------------------------------------------------------------
def Lin_Sim(i, j, non_geo_ff, non_geo_da, mat, lr, sam_mat, sam_lr):
    """ Compute Lin similarity. Lin similarity works on non-geographic attributes.
        """
    # In order to reduce calculation time, this routine evaluates the similarity between node i and node j on the sampled matrix sam_mat
    ak=numpy.transpose((non_geo_ff, non_geo_da))
    # I have to copy all the matrix in order to find how many agents share the same attributes as the two ones considered here.
    sel=numpy.copy(sam_mat)
    
    for ii in ak:
        check=mat[ii[0]][i]-mat[ii[0]][j]
        if check==0:
            sel=sel[sel[ii[0]]==mat[ii[0]][i]]
        else:
            if ii[1]=='o':
                if check>0:
                    sel=sel[mat[ii[0]][i]>=sel[ii[0]]]
                    sel=sel[sel[ii[0]]>=mat[ii[0]][j]]
                else:
                    sel=sel[mat[ii[0]][j]>=sel[ii[0]]]
                    sel=sel[sel[ii[0]]>=mat[ii[0]][i]]

# Since attributes are dependent, the only way to handle this thing is
# to consider the frequence of agents sharing all attributes shared by the two analysed here.
# If they do not share an attribute and the attribute is ordinal, the number of agents sharing attributes between the two values are considered.
# Otherwise, if the attribute is a categorical datum, no selection is considered.
# The idea is that the lowest the number of agents sharing the same attribute,
# the most information this shared attribute it contains about the two agents.
# If attributes were independent, I could have had considered attributes independently and then sum different contribution.
# Since they are not, I have to consider the probability of observing at the same time all different attributes.
cab=len(sel)
    db=len(sam_mat[sam_mat==mat[j]])
    da=len(sam_mat[sam_mat==mat[i]])
    
    if cab==0:
        # if the superposition is zero on the sample, then there is not even any agent with the same characteristic of either i or j (is it true?).
        # In this sense, the probability of finding something with the same feature of both i and j
        # is really small on the whole set and thus not jsut they are unlikely but their superposition is too.
        # Think that if they are really different, the probability of their superposition is going to be higher (thus the information carried smaller).
        return 1
elif da==0 and db!=0:
    # if there is not any agent as i, we can assume that is the only one with this characteristic in the whole set.
    # It is a strong assumption, but it is more conservative:
    # the information carried by her/him is going to be overestimated, thus making the similarity underestimated (in a sense we are limiting false positives).
    # If a is the only one, then numpy.log(da_{over the whole set}=1)=0
    return 2.*(-numpy.log2(cab)+numpy.log2(sam_lr))/(numpy.log2(sam_lr)+numpy.log2(lr)-numpy.log2(db))
    elif db==0 and da!=0:
        # the same thing for j
        return 2.*(-numpy.log2(cab)+numpy.log2(sam_lr))/(numpy.log2(sam_lr)+numpy.log2(lr)-numpy.log2(da))
elif db==0 and da==0:
    # the same thing for j
    return 2.*(-numpy.log2(cab)+numpy.log2(sam_lr))/(2.*numpy.log2(lr))
    else:
        return 2.*(-numpy.log2(cab)+numpy.log2(sam_lr))/(2.*numpy.log2(sam_lr)-numpy.log2(da)-numpy.log2(db))
# since they are all frequencies, I can consider the lenght of the selection and the lenght of the selection separately.

def Net_ij(i, j, hss_0, damp, non_geo_ff, non_geo_da, mat, lr, sam_mat, sam_lr):
    """ Compute geographicly damped Lin similarity.
        The input data are structured.
        """
    if damp>0:
        sim_geo_hh=GeoSim(hss_0, damp, mat['hh_lat'][i], mat['hh_lon'][i], mat['hh_lat'][j], mat['hh_lon'][j])
        sim_geo_wp=GeoSim(hss_0, damp, mat['wp_lat'][i], mat['wp_lon'][i], mat['wp_lat'][j], mat['wp_lon'][j])
    else:
        sim_geo_hh=GeoExpDamp(hss_0, mat['hh_lat'][i], mat['hh_lon'][i], mat['hh_lat'][j], mat['hh_lon'][j])
        sim_geo_wp=GeoExpDamp(hss_0, mat['wp_lat'][i], mat['wp_lon'][i], mat['wp_lat'][j], mat['wp_lon'][j])
    # For the moment, it selects the greater between the workplace and the household distance
    sim_geo=max([sim_geo_hh,sim_geo_wp])
    # if the distance is less than a certain threshold, the Lin value is calculated, otherwise it is disregarded
    if sim_geo>GLOBAL_SIM_TH:
        return sim_geo*Lin_Sim(i, j, non_geo_ff, non_geo_da, mat, lr, sam_mat, sam_lr)
    else:
        return 0.

# ----------------------------------------------------------------------------------------
#        the LS4HD class BEGINS
# ----------------------------------------------------------------------------------------
class LS4HD:
    """
        Lin Similarity 4 Heterogeneous Data
        
        In this code we assume (implicitly) that rows are agents and columns are features,
        such that
        
        >>> len(description_array)==lc
        True
        
        :param data:
        :param da:
        :param ff:
        """
    def __init__(self, o_path, comm, data, da, ff, hss=5000, damping=0, chunk_dim=1e3, sam_p=1e-1):
        self.comm=comm
        self.rank=comm.Get_rank()
        self.size=comm.Get_size()
        
        if self.rank==0:
            # processor 0 is the root
            logging.info(' Have a nice day from processor # {}'.format(self.rank))
            sys.stdout.flush()
        
        self.o_path=o_path
        self.cd=chunk_dim
        
        self.mat=data
        self.da=da
        self.ff=ff
        
        self.lr=len(self.mat)
        
        ##################################################
        # SAMPLING!
        
        # The main difference w.r.t. the previous version is that this one,
        # in order to reduce calculation times it sample the original dataset and calculates
        # the similarity on it.
        
        self.sam_lr=int(self.lr*sam_p)
        # I take the sample to be a certain percentage of the original dataset. The default value is 10%
        if self.rank==0:
            sampled_rows=numpy.random.choice(self.lr, self.sam_lr, replace=False)
        else:
            sampled_rows=numpy.empty(self.sam_lr, dtype='i')
        self.comm.Bcast([sampled_rows, self.sam_lr, MPI.INT], root=0)
        # The previous command send  the list of the sampled agents to all processors
        self.sam_mat=self.mat[sampled_rows]
        
        
        
        
        sh_aux=numpy.zeros(1)
        self.damp=damping
        
        
        
        self.non_geo=numpy.where(self.da!='g')[0]
        self.geo=numpy.where(self.da=='g')[0]
        # I had geo since I tags should not be confused
        
        self.non_geo_ff=self.ff[self.non_geo]
        self.non_geo_da=self.da[self.non_geo]
        
        # It is better if all processors knows which are the non_geo attributes on its own.
        
        
        
        start_end=None
        # This is set to None since it is going to be calcualted by the root only and the send in the self.start_end of each processor by root
        self.start_end=numpy.zeros(2, dtype='i8')
        
        total_n=(self.lr-1)*self.lr/2
        logging.info(' lr='+str(int(self.lr))+' total_n='+str(int(total_n))+' # '+str(self.rank))
        # it returns the total number of nodes and the total number of couples
        
        sys.stdout.flush()
        #TODO here we estimate the effort taken by process for load balancing
        self.effort=numpy.floor(1.*total_n/self.size)*numpy.ones(self.size)
        remainder=total_n % self.size
        for i in xrange(self.size):
            if i<remainder:
                self.effort[i]+=1
        logging.info(' efforts='+str(int(self.effort[self.rank]))+' # '+str(self.rank))
        
        sys.stdout.flush()
        # efforts are opportunely distributed
        
        
        
        # root calculates the efforts per processor and the starting and ending couple
        if self.rank==0:
            
            total_n=(self.lr-1)*self.lr/2
            start_end=numpy.zeros((self.size, 2), dtype='i8')
            for i in xrange(self.size):
                # starting point
                if i==0:
                    start_end[i, :2]=[0,1]
                else:
                    start_end[i, 0]=start_end[i-1,0]
                    start_end[i, 1]=start_end[i-1,1]+1
                    aux=numpy.copy(self.effort[i])
                    while aux>0:
                        if aux>self.lr-start_end[i, 1]:
                            aux-=self.lr-start_end[i, 1]
                            start_end[i, 0]+=1
                            start_end[i, 1]=start_end[i, 0]+1
                        else:
                            start_end[i, 1]+=aux-1
                            aux=0
                                self.comm.Scatter(start_end, self.start_end, root=0)
                                    # The previous command gives all process its starting point. It is going to be crucial in the end
                                    
                                    self.hss=hss
                                        
                                        #TODO why do we adjust hhs_0? What is the purpose of hss_0 vs hss?
                                        if self.damp!=1 and self.damp!=0:
                                            self.hss_0=1.*hss/(numpy.power(2, self.damp)-1)
                                                # the value has to be adjusted for power laws
                                                else:
                                                    self.hss_0=hss
                                                        
                                                        
                                                        logging.info(' Initialisation ended. Process '+str(self.rank)+' of '+str(self.size))
                                                            sys.stdout.flush()
                                                                
                                                                self.Sim_master()

def Sim_master(self):
    
    with h5py.File(os.path.join(self.o_path,'Piedmont_hss_'+str(int(self.hss))+'_d_'+str(self.damp)+'.h5'), 'w', driver='mpio', comm=self.comm, libver='latest') as f:
        # definition of the group
        h5_group=f.create_group('SimNet')
            # definition of the dataset
            al=h5_group.create_dataset('adj_list', (self.lr*(self.lr-1)/2,), dtype=[('src_node','i8'), ('trg_node','i8'), ('weight','f8')], chunks=True)
            
            logging.info(' File created. Process '+str(self.rank)+' of '+str(self.size)+' starting the calculation')
            
            sys.stdout.flush()
            #TODO ?couple: pair of indices
            couple=self.start_end[:2]
            counter=0
            offset=0
            
            for i in xrange(self.rank):
                offset+=int(self.effort[i]) # offset in HDF5
            # offset count how many entries in the dataset I have to skip to put data in the right place
            
            # TODO? weight, meaning of buffer_g
            # add a buffer for data. It is structured.
            # TODO? chunk dim
            buffer_g=numpy.zeros(self.cd, dtype=[('src_node','i8'), ('trg_node','i8'), ('weight','f8')])
            
            
            start=dt.datetime.now()
            for i in xrange(int(self.effort[self.rank])):
                chunk_aux=i % self.cd #TODO?
                # when I have reached the chunk size I will copy data to file. chunk_aux takes into account it.
                aux=Net_ij(int(couple[0]), int(couple[1]), self.hss_0, self.damp, self.non_geo_ff, self.non_geo_da, self.mat, self.lr, self.sam_mat, self.sam_lr)
                buffer_g[chunk_aux]=(int(couple[0]), int(couple[1]),aux)
                # Here are some messages in order to control the evaluation. The ETA is estimated from the calculation time so far.
                if i==0:
                    logging.info(' Started! # '+str(self.rank))
                    sys.stdout.flush()
                elif i==2000:
                    so_far=dt.datetime.now()-start
                    # TODO? tpe eta_h/eta_m
                    tpe=1.*so_far.seconds/(i+1)
                    # time per evaluation
                    eta_h=int(tpe*(self.effort[self.rank]-i)/3600)
                    eta_m=int(((tpe*(self.effort[self.rank]-i))%3600)/60)
                    logging.info(' First 2000 couples processed. ETA '+str(eta_h).zfill(2)+':'+str(eta_m).zfill(2)+' # '+str(self.rank))
                    sys.stdout.flush()
                elif i % int(self.effort[self.rank]/10)==0:
                    so_far=dt.datetime.now()-start
                    tpe=1.*so_far.seconds/(i+1)
                    # time per evaluation
                    eta_h=int(tpe*(self.effort[self.rank]-i)/3600)
                    eta_m=int(((tpe*(self.effort[self.rank]-i))%3600)/60)
                    logging.info(' '+str(10*i/int(self.effort[self.rank]/10))+'%. ETA '+str(eta_h).zfill(2)+':'+str(eta_m).zfill(2)+' # '+str(self.rank))
                # checking memory usage
                mem = psutil.virtual_memory()
                if mem.available<=100 * 1024 * 1024:
                    #100 MB
                    logging.info(' We are running out of memory! # '+str(self.rank))
                    sys.stdout.flush()
                # checking swap memory
                swap=psutil.swap_memory()
                if swap.percent>.9:
                    logging.info(' The swap is occupied at the 90%! # '+str(self.rank))
                    sys.stdout.flush()
                
                
                # it goes to following couple
                if couple[1]<self.lr-1:
                    couple[1]+=1
                else:
                    couple[0]+=1
                    couple[1]=couple[0]+1
                
                
                # if the chunk is full copies it to file
                if chunk_aux==self.cd-1:
                    al[offset:offset+int(self.cd)]=buffer_g
                    # it resets the buffer to an empty vector
                    buffer_g=numpy.zeros(self.cd, dtype=[('src_node','i8'), ('trg_node','i8'), ('weight','f8')])
                    # it updates the offset. it is necessary for the last saving
                    offset=+int(self.cd)
                    chunk_aux=0
    # the last saving
                        al[offset:offset+chunk_aux]=buffer_g[:chunk_aux]
                            
                            
                            logging.info(' File closed. # '+str(self.rank))
                                sys.stdout.flush()


#----------------------------------------------------------------------------------------
#        the LS4HD class ENDS
#----------------------------------------------------------------------------------------
def main():
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt=':%Y-%m-%d %H:%M:%S', level=logging.INFO)
    
    # comm = MPI.COMM_WORLD
    # rank = comm.Get_rank()
    # size = comm.Get_size()
    # logging.info("Process {0} from {1}".format(rank, size))
    
    parser = get_parser()
    args = parser.parse_args()
    
    home=str(args.i_path)
    outpath=str(args.o_path)
    #if outpath=='./':
    #    outpath='/vdb1/sarawalk/Piedmont_out/'
    
    start=MPI.Wtime()
    
    logging.info(GeoDist([1,2], [2,1], [3,1], [4,2]))
    data, da, ff=preprocessing(home)
    LS4HD(outpath, MPI.COMM_WORLD, hss=int(args.hss), damping=int(args.damp), chunk_dim=10**3, data=data, da=da, ff=ff, sam_p=args.sam_p)
    
    time_taken=MPI.Wtime()-start
    logging.info('Time taken='+str(int(time_taken)/3600)+' h and '+str((int(time_taken)%3600/60))+' m. # '+str(MPI.COMM_WORLD.Get_rank()))
    sys.stdout.flush()
    return 0

if __name__ == "__main__":
    main()