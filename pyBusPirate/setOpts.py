'''
  setOpts.py module

  Process Command-Line Options in uniform way for 
  different purposes, hopefully all covered here.

  End result: 

    setOpts.args is an object with attributes,

       args.jsonfile
       args.rssithreshold
       args.window
       args.minspan
       args.screen

'''
import argparse
parser = argparse.ArgumentParser(description='Process Observation JSON XZ file.')
parser.add_argument('json', metavar='jsonfile', help='JSON XZ file')
parser.add_argument('--rssithreshold', metavar='rssithreshold', nargs='?',
	    default='57', help='RSSI "close" threshold')
parser.add_argument('--window', metavar='window', nargs='?',
	    default=None, help='Window (seconds) defining contact')
parser.add_argument('--minspan', metavar='minspan', nargs='?',
	    default=None, help='Span (minutes) defining contact')
parser.add_argument('--maxcontam', metavar='maxcontam', nargs='?',
	    default=None, help='Window (seconds) defining contamination')
parser.add_argument('--screen', metavar='screen', nargs='?',
	    default=None, help='whether to screen contacts')
args = parser.parse_args()
args.rssithreshold = int(args.rssithreshold) 
if args.window: args.window = int(args.window)
if args.maxcontam: args.maxcontam = int(args.maxcontam)
if args.minspan: args.minspan = int(args.minspan)
if args.screen: args.screen = args.json
