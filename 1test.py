import csv
import re
import numpy as np
import math
import matplotlib.pyplot as plt
import datetime
import statistics
import scipy.stats as stats
import scipy.special as sps
from scipy.stats import gamma

mu, sigma = 1.5, 0.5 # mean and standard deviation
s = np.random.lognormal(mu, sigma, 1000)
n = len(s)

def get_data(filename, col):
    with open(filename, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='|')
        ret = []
        for row in reader:
            if len(row) > col and re.match('\d+:\d+:\d+', row[col]):
                time = datetime.datetime.strptime(row[col], '%H:%M:%S').time()
                ret.append((60 * time.minute) + time.second)
        return ret


def print_stats(data):
    cov = stats.variation(data)
    print(f'cov {stats.variation(data):6.3f}', f'\tskew {stats.skew(data):.3f}')

arrival_times = get_data('Project2 Data Sets/arrival_aggregated.csv', 1)
order_times = get_data('Project2 Data Sets/order_aggregated.csv', 2)
payment_times = get_data('Project2 Data Sets/payment_aggregated.csv', 2)
pickup_times = get_data('Project2 Data Sets/pickup_aggregated.csv', 2)

#print_stats(arrival_times) # Exponential
#print_stats(order_times) # Gamma
#print_stats(payment_times) # Gamma
#print_stats(pickup_times) # Gamma

estimator = len(arrival_times)/np.sum(arrival_times)

# read data from a file
with open('data.dat', 'r') as infile:
    s = [float(value) for value in infile.readlines()]
    infile.close()

plots = [arrival_times, order_times, payment_times, pickup_times]

stat_arr = []
figure, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2)
figures = [ax1, ax2, ax3, ax4]
current_fig = 0

for plot in plots:
    c_plt = figures[current_fig] # assign current plot
    if plot == plots[0]:
        # Sort the data
        plot.sort()

        # Plot the histogram
        count, bins, ignored = c_plt.hist(plot, int(len(plot)**(1/2)*2), density=True, align='mid')
        stat_arr.append([count, bins, ignored])

        # Make a PDF
        x = np.linspace(min(bins), max(bins), 10000)
        estimator = len(plot) / np.sum(plot)
        estimator = 1 / np.average(plot)
        pdf = (estimator * np.exp(-(estimator * x)))

        # Plot the PDF
        c_plt.plot(x, pdf, linewidth=2, color='r')
    else:
        # Sort the data
        plot.sort()

        # Plot the histogram
        count, bins, ignored = c_plt.hist(plot, int(len(plot)**(1/2)*2), density=True, align='mid')
        stat_arr.append([count, bins, ignored])

        # Make a PDF
        shape, loc, scale = gamma.fit(order_times)
        x = np.linspace(min(bins), max(bins), 10000)
        pdf = x**(shape-1) * (np.exp(-x/scale) / (sps.gamma(shape) * scale**shape))
        # Plot the PDF
        c_plt.plot(x, pdf, linewidth=2, color='r')

    current_fig += 1


# superimpose an exponential distribution pdf
#x = np.linspace(min(stats[0][1]), max(stats[0][1]), 10000)
#pdf = (estimator * np.exp(-(estimator * x)))
#plt.plot(stats[0][1], pdf, linewidth=2, color='r')

#shape, loc, scale = gamma.fit(order_times)
#x = np.linspace(min(stat_arr[0][1]), max(stat_arr[0][1]), 10000)
#pdf = x**(shape-1) * (np.exp(-x/scale) / (sps.gamma(shape) * scale**shape))
#plt.plot(x, pdf, linewidth=2, color='r')

# estimate parameters from data
sum = 0
for v in s:
    sum = sum + np.log(v)
mu = sum / n

sum = 0
for v in s:
    sum = sum + (np.log(v) - mu)**2
sigma = math.sqrt(sum / n)

#x = np.linspace(min(bins), max(bins), 10000)
#pdf = (np.exp(-(np.log(x) - mu)**2 / (2 * sigma**2))
       #/ (x * sigma * np.sqrt(2 * np.pi)))
#plt.plot(x, pdf, linewidth=2, color='y')


plt.axis('tight')
plt.show()
