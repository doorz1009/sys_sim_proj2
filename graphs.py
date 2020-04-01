import csv
import re
import numpy as np
import matplotlib.pyplot as plt
import datetime
import scipy.stats as stats
import scipy.special as sps
from scipy.stats import gamma
from scipy.integrate import quad


arrival_count = 189
order_count = 188
payment_count = 184
pickup_count = 129
count_arr = [arrival_count, order_count, payment_count, pickup_count]

def get_data(filename, col):
    with open(filename, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='|')
        ret = []
        for row in reader:
            if len(row) > col and re.match('\d+:\d+:\d+', row[col]):
                time = datetime.datetime.strptime(row[col], '%H:%M:%S').time()
                ret.append((60 * time.minute) + time.second)
        return ret


def exponential_integrand(x, estimator):
    return (estimator * np.exp(-(estimator * x)))


def gamma_integrand(x, shape, scale):
    return (x ** (shape - 1) * (np.exp(-x / scale) / (sps.gamma(shape) * scale ** shape)))


def logn_integrand(x, mu, sigma):
    return (np.exp(-(np.log(x) - mu) ** 2 / (2 * sigma ** 2)) / (x * sigma * np.sqrt(2 * np.pi)))


def print_stats(data):
    cov = stats.variation(data)
    print(f'cov {stats.variation(data):6.3f}', f'\tskew {stats.skew(data):.3f}')

arrival_times = get_data('Project2 Data Sets/arrival_aggregated.csv', 1)
order_times = get_data('Project2 Data Sets/order_aggregated.csv', 2)
payment_times = get_data('Project2 Data Sets/payment_aggregated.csv', 2)
pickup_times = get_data('Project2 Data Sets/pickup_aggregated.csv', 2)

estimator = len(arrival_times)/np.sum(arrival_times)

# read data from a file
with open('data.dat', 'r') as infile:
    s = [float(value) for value in infile.readlines()]
    infile.close()

plots = [arrival_times, order_times, payment_times, pickup_times]
plot_names = ['arrival_times', 'order_times', 'payment_times', 'pickup_times']
current_plot = 0
for plot in plots:
    if plot == plots[0]:
        # Plot the histograms
        plt.title(plot_names[current_plot])
        # The following histogram is to get real counts to compare in the chi square statistic.
        actual, bins, ignored = plt.hist(plot, 20, density=False, align='mid', color='b')
        plt.figure()
        plt.title(str(f'{plot_names[current_plot]} with PDF'))
        count, bins, ignored = plt.hist(plot, 20, density=True, align='mid', color='b')

        x = np.linspace(min(bins), max(bins), 10000) # Make a PDF
        estimator = 0.025
        pdf = (estimator * np.exp(-(estimator * x)))

        expected_vals = []
        total_items = np.sum(actual)
        for i in range(len(bins) - 1):
            # Get area under curve for the width of each bin.
            expected_vals.append(quad(exponential_integrand, bins[i], bins[i + 1], args=(estimator))[0] * total_items)

        print(f"Estimator: {estimator}")
        print(stats.chisquare(actual, expected_vals), int(len(plot)**(1/2)))

        plt.plot(x, pdf, linewidth=2, color='r') # Plot the PDF
    else:
        plt.figure() # Make a new window

        # Plot the histograms
        plt.title(plot_names[current_plot])
        # The following histogram is to get real counts to compare in the chi square statistic.
        actual, bins, ignored = plt.hist(plot, int(len(plot)**(1/2)), density=False, align='mid', color='b')
        plt.figure()
        plt.title(str(f'{plot_names[current_plot]} with PDF'))
        count, bins, ignored = plt.hist(plot, int(len(plot)**(1/2)), density=True, align='mid', color='b')

        # Make a PDF
        shape, loc, scale = gamma.fit(plot)
        if current_plot == 2:
            shape, scale = 2.6, 20 # The other graphs fit well automatically, this one needs intervention though.

        x = np.linspace(min(bins), max(bins), 10000)
        pdf = x**(shape-1) * (np.exp(-x/scale) / (sps.gamma(shape) * scale**shape))

        expected_vals = []
        total_items = np.sum(actual)
        for i in range(len(bins) - 1):
            # Get area under curve for the width of each bin.
            expected_vals.append(quad(gamma_integrand, bins[i], bins[i + 1], args=(shape, scale))[0] * total_items)

        print(f"shape: {shape}\tloc: {loc}\tscale: {scale}")
        print(stats.chisquare(actual, expected_vals), int(len(plot)**(1/2)))

        plt.plot(x, pdf, linewidth=2, color='r') # Plot the PDF

    current_plot += 1


plt.axis('tight')
plt.show()
