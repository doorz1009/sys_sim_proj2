import random
import numpy as np
from numpy.random import gamma
import simpy


RANDOM_SEED = 12345
NUMBER_OF_CUSTOMERS = 30000

# Setup and start the simulation
random.seed(RANDOM_SEED)
env = simpy.Environment()
RUN_TIL = 0

MEAN_INTERARRIVAL_TIME = 0.025

# Make these be resources so we don't get race condition for increment
BALK_TOTAL = simpy.Resource(env, NUMBER_OF_CUSTOMERS + 1)

CUSTOMER_COUNT = simpy.Resource(env, NUMBER_OF_CUSTOMERS + 1)

# Debug variables:
PRINT_DEBUG_MESSAGES = False
TIME_DEBUGGING = False

CUSTOMER_TOTAL_TIME = []


def customer_generator(env, number, mean_interarrival_time, lanes, stations):
    """
        Generates customers for both scenarios
    """
    for i in range(number):
        c = customer(env, 'Customer%02d' %
                            i, lanes, stations)
        global CUSTOMER_COUNT
        CUSTOMER_COUNT.request()

        env.process(c)
        interarrival_time = np.random.exponential(1/mean_interarrival_time)
        yield env.timeout(interarrival_time)


def customer(env, name, lanes, stations):
    """
        Customer arrives, is served and leaves.
        lanes: order, pay, pickup
        stations: order, pay, pickup
    """
    if lanes[0].count == lanes[0].capacity:
        # LINE IS FULL, LEAVEEE
        if PRINT_DEBUG_MESSAGES:
            print("I'm outta here! I don't have time for this!")
            print(lanes[0].count, lanes[1].count, lanes[2].count)
            print(stations[0].count, stations[1].count, stations[2].count)
        global BALK_TOTAL
        BALK_TOTAL.request()
        return

    start = env.now
    lane_req = None

    # Occupy a spot in the lane that you picked.
    lane_req = lanes[0].request()

    # Get in line for the order station.
    station_req = stations[0].request()

    # Wait until it is your turn to order.
    yield station_req

    if PRINT_DEBUG_MESSAGES:
        print("%s is placing their order at time %d" % (name, env.now))

    # Place your order
    order_time = gamma(1.6361, 25.834)
    if TIME_DEBUGGING:
        print("Order_time: %d" % order_time)

    yield env.timeout(order_time)

    payment_lane_req = lanes[1].request()

    if PRINT_DEBUG_MESSAGES:
        print("%s is waiting for a spot in the pickup lane" % name)

    yield payment_lane_req

    # Once you've got a spot in the pickup lane, release your spot in
    # the lane you picked and the order station for that lane
    stations[0].release(station_req)
    lanes[0].release(lane_req)

    # Request payment window resource
    payment_window_req = stations[1].request()

    yield payment_window_req

    if PRINT_DEBUG_MESSAGES:
        print("%s is now at the payment window and is about to pay" % name)

    # Once the resource is acquired, begin payment timeout
    # payment_time = random.expovariate(1.0 / MEAN_PICKUP_TIME) # TODO: Use my distribution here
    payment_time = gamma(2.6, 20)
    if TIME_DEBUGGING:
        print("payment_time: %d" % payment_time)

    yield env.timeout(payment_time)

    pickup_lane_req = lanes[2].request()

    yield pickup_lane_req

    # Once you've got a spot in the pickup lane, release your spot in
    # the lane you picked and the order station for that lane
    lanes[1].release(payment_lane_req)
    stations[1].release(payment_window_req)

    # Request payment window resource
    pickup_window_req = stations[2].request()

    yield pickup_window_req

    if PRINT_DEBUG_MESSAGES:
        print("%s is now at the pickup window and is about to get their food" % name)

    # Once the resource is acquired, begin payment timeout
    # pickup_time = random.expovariate(1.0 / MEAN_PICKUP_TIME) # TODO: Use my distribution here
    pickup_time = gamma(1.1461, 38.3244)
    if TIME_DEBUGGING:
        print("pickup_time: %d" % pickup_time)
    yield env.timeout(pickup_time)

    CUSTOMER_TOTAL_TIME.append(env.now - start)

    lanes[2].release(pickup_lane_req)
    stations[2].release(pickup_window_req)

    if PRINT_DEBUG_MESSAGES:
        print("%s has now paid their bill and received their food" % name)


def run_sim():
    # Get all the globals that we have to modify.
    global MEAN_ORDER_TIME
    global MEAN_PICKUP_TIME

    global BALK_TOTAL

    global CUSTOMER_COUNT

    global RUN_TIL
    global CUSTOMER_TOTAL_TIME

    # Keeps track of how long each customer is in the line
    CUSTOMER_TOTAL_TIME = []

    BALK_TOTAL = simpy.Resource(env, NUMBER_OF_CUSTOMERS + 1)

    CUSTOMER_COUNT = simpy.Resource(env, NUMBER_OF_CUSTOMERS + 1)

    # Interval vars
    INTERVAL = 3600  # Approximately 3 hours if each time unit is a second
    RUN_TIL += INTERVAL

    # Allocate resources for each initial lane, the order stations, and the second merged lane.
    lane_1 = simpy.Resource(env, 9)  # Order lane
    lane_2 = simpy.Resource(env, 3)  # Payment lane
    lane_3 = simpy.Resource(env, 2)  # Pickup lane

    order_station = simpy.Resource(env)
    payment_window = simpy.Resource(env)
    pickup_window = simpy.Resource(env)

    # Put lanes into lists for ease of passing around
    lanes = [lane_1, lane_2, lane_3]
    stations = [order_station, payment_window, pickup_window]

    # Fill the pipeline by running for 3 hours
    env.process(customer_generator(
        env, NUMBER_OF_CUSTOMERS, MEAN_INTERARRIVAL_TIME, lanes, stations))
    env.run(RUN_TIL)

    # Note the starting values for the simulation
    start_cst_cnt = CUSTOMER_COUNT.count
    start_blk_cnt = BALK_TOTAL.count

    run_balk = []

    last_balk_cnt = 0
    last_cst_cnt = start_cst_cnt
    # Start processes and run, fill the pipeline
    while CUSTOMER_COUNT.count < NUMBER_OF_CUSTOMERS:
        random.seed(random.random() * 10000000)
        RUN_TIL += INTERVAL

        env.run(RUN_TIL)
        # Append (number of customers simulated, number that balked)
        run_balk.append((CUSTOMER_COUNT.count - last_cst_cnt, BALK_TOTAL.count - last_balk_cnt))

        # Since the two resources below are cumulative, keep track of
        # how much has changed since the last run
        last_balk_cnt = BALK_TOTAL.count
        last_cst_cnt = CUSTOMER_COUNT.count

    avg_cust_time = sum(CUSTOMER_TOTAL_TIME) / len(CUSTOMER_TOTAL_TIME)
    # Clear the list
    CUSTOMER_TOTAL_TIME = []
    # Ensure that there are no more processes to be done.
    env.run()

    # The total number of customers that are accurately simulated
    # after the pipeline is filled.
    customers_simulated = NUMBER_OF_CUSTOMERS - start_cst_cnt

    # Balking numbers adjusted to remove the balks that occur
    # when the pipeline is being filled.
    adjusted_balk = BALK_TOTAL.count - start_blk_cnt

    # Customer numbers that result from the number of customers that
    # are accurately simulated with their ajusted balk numbers removed.
    adjusted_customers = customers_simulated - adjusted_balk

    balk_percentages = [] # List of balk percentage for each run
    cust_served_per_run = []
    for pair in run_balk:
        # Each pair within this list is comprised of the number of the number of customers simulated
        # at the end of the time period and the number of balks at the end of the time period
        balk_percentages.append(float(pair[1]) / float(pair[0]))
        cust_served_per_run.append(pair[0] - pair[1])

    cust_per_run_avg = float(sum(cust_served_per_run)) / float(len(cust_served_per_run))
    balk_avg = sum(balk_percentages) / len(balk_percentages)

    print("\nOVERALL STATISTICS:")
    print('{0: <28}{1: <5}\n{2: <28}{3: <5}\n{4: <28}{5: <5}\n{6: <28}{7: <5}'.format(
            "Customers Simulated:", "%d" % customers_simulated,
            "Customers Served:", "%d" % adjusted_customers,
            "Balk total:", "%d" % BALK_TOTAL.count,
            "Average balk rate:", "%0.2f%%" % (balk_avg * 100.0)))
    print("Average time spent in line: %0.2f" % avg_cust_time)
    print("Average customers served per run: %0.2f" % cust_per_run_avg)


for i in range(5):
    run_sim()

print("FINISHED")