#!/usr/bin/python

# copyright Red E Tools Ltd.
# MIT License

import argparse
import logging
import sys
import time

from classes.session import Session
from classes.svg import SVG
from classes.grbl import GRBL
from lib import stipple
from lib import pixel2laser as p2l

def main():
    '''
    This function does nothing else than parsing command line arguments.
    It delegates to library functions accordingly.
    '''
    log_format = '%(asctime)s %(levelname)s %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_format)
    
    parser = argparse.ArgumentParser(description='This program is a box full of useful CNC tools')
    
    # Set up sub-commands like git uses them
    subparsers = parser.add_subparsers(help="Available subcommands")
    
    # define arguments for the 'stipple' subcommand
    stipple_parser = subparsers.add_parser(
        "stipple",
        help="Creates stippling art for laser-engraving based on files created by third-party C++ programs voronoi_stippler and concorde.",
        epilog="EXAMPLE: python ./cnctoolbox.py stipple ./data/grace.crd ./data/grace.sol out.svg --weight ./data/grace.wgt"
        )
    stipple_parser.add_argument(
        'crd_file',
        metavar='COORD_FILE',
        help='File containing point coordinates in concorde format. Use modified voronoi_stippler to generate it.'
        )
    stipple_parser.add_argument(
        'idx_file',
        metavar='INDEX_FILE',
        help='File containing TSP indices in concorde format. Use concorde to solve the TSP problem.'
        )
    stipple_parser.add_argument(
        'out_file',
        metavar='OUT_FILE',
        help='File to write the result to. Currently only .svg output is supported. Gcode output will be supported soon.'
        )
    stipple_parser.add_argument(
        '--weight',
        metavar='WEIGHT_FILE',
        help='File containing weights for each point. Use modified voronoi_stippler to generate it.'
        )
    
    # define arguments for the 'p2l' (pixel2laser) subcommand
    p2l_parser = subparsers.add_parser(
        "pixel2laser",
        help="Generate optimized Gcode from PNG for laser.",
        epilog="EXAMPLE: python ./cnctoolbox.py p2l ./data/pixel2laser.png p2l.ngc"
        )
    p2l_parser.add_argument(
        'in_file',
        metavar='IN_FILE',
        help='PNG file to be read. Other file formats have not been tested.'
        )
    p2l_parser.add_argument(
        'out_file',
        metavar='OUT_FILE',
        help='File to write the result to.'
        )
    
    # define arguments for the 'stream' subcommand
    stream_parser = subparsers.add_parser("stream", help="Streams a gcode file to GRBL.")
    stream_parser.add_argument(
        'dev_node',
        metavar='DEV_NODE',
        help='Interface node in /dev file system. E.g. /dev/ttyACM0'
        )
    stream_parser.add_argument(
        'gcodefile',
        metavar='GCODE_FILE',
        help='File to stream'
        )
    
    # define arguments for the 'bbox' subcommand
    bbox_parser = subparsers.add_parser("bbox", help="Calculates the bounding box of a gcode file")
    
    # define arguments for the 'scale' subcommand
    scale_parser = subparsers.add_parser("scale", help="Scales coordinates in a gcode file")

    args = parser.parse_args()
    subcmd = sys.argv[1]
    
    # after all arguments have been parsed, delegate
    if subcmd == "stipple":
        stipple.do(args.crd_file, args.idx_file, args.weight, args.out_file)
        
    elif subcmd == "pixel2laser":
        p2l.do(args.in_file, args.out_file)
        
    elif subcmd == "stream":
        grbl = GRBL("grbl1", args.dev_node)
        grbl.cnect()
        time.sleep(2)
        grbl.poll_start()
        grbl.set_streamingfile(args.gcodefile)
        grbl.run()
        
    elif subcmd == "bbox":
        print("to be implemented soon")
        
    elif subcmd == "scale":
        print("to be implemented soon")


if __name__ == "__main__":
    main()