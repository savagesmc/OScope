#!/usr/bin/env python3

import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt

def doPlot(fname):

    vals = []

    with open(fname, 'r') as f:
        lines = f.readlines()
        vals = np.array([float(val.strip()) for val in lines])

    print(f"Mean:      {np.mean(vals)}")
    print(f"StdDev:    {np.std(vals)}")
    print(f"Biggest:   {np.max(vals)}")
    print(f"Smallest:  {np.min(vals)}")

    plt.plot(vals)
    plt.show()


doPlot("chil.txt")
doPlot("ptp.txt")

