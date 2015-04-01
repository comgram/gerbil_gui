#!/usr/bin/python

import logging
from classes.svg import SVG

def do(crd_file, idx_file, wgt_file, out_file):
    coords_unsorted = read_coords(crd_file)
    sort_indices = read_sort_indices(idx_file)
    if wgt_file:
        weights_unsorted = read_weights(wgt_file)
        
    data = merge_and_sort_data(sort_indices, coords_unsorted, weights_unsorted)
        
    if ".svg" in out_file:
        svg = SVG("mysvg", out_file)
        svg.draw_from_data(data, False)
        svg.save()
    else:
        print("Only supporting .svg output at the moment")

def merge_and_sort_data(sort_indices, coords_unsorted, weights_unsorted):
    logging.info("Sorting coords")
    data = []
    for i in sort_indices:
        data.append(coords_unsorted[i] + (weights_unsorted[i],))
    return data


def read_sort_indices(filename_solution):
    logging.info("Reading solution file %s", filename_solution)
    f = open(filename_solution)
    sort_indices = []
    f.next() # skip the first line which contains the index length
    for line in f:
        indices = map(int, line.strip().split(" "))
        sort_indices.append(indices)
        
    return [item for sublist in sort_indices for item in sublist]


def read_weights(filename_weights):
    logging.info("Reading weight file %s", filename_weights)
    f = open(filename_weights)
    weights = []
    for line in f:
        idx, w = line.strip().split(' ')
        weights.append(float(w))
        
    return weights
    
    
def read_coords(filename_coord):
    '''
    read the coordinates from file
    coords are stored in concorde format
    '''
    logging.info("Reading coord file %s", filename_coord)
    f = open(filename_coord)
    
    coords=[]
    state_coords = False
    for line in f:
        if "NODE_COORD_SECTION" in line:
          state_coords = True
          continue
        if "EOF" in line:
          state_coords = False
        if state_coords == True:
          i, x, y = line.strip().split(' ')
          coords.append((float(x), float(y)))
    return coords