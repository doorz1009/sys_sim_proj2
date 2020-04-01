import random
import simpy
import statistics


RANDOM_SEED = 12345
NUMBER_OF_CUSTOMERS = 30000

# Setup and start the simulation
random.seed(RANDOM_SEED)
env = simpy.Environment()
RUN_TIL = 0

MEAN_INTERARRIVAL_TIME = 4.0  # Generate new customers roughly every x time units
MEAN_ORDER_TIME = 2.0
MEAN_PICKUP_TIME = 2.0
MEAN_FOOD_PREP_TIME = 5.0

# Statics:
TOTAL_ORDER_TIME = 0.0
TOTAL_PREP_TIME = 0.0
TOTAL_PICKUP_TIME = 0.0

# Make these be resources so we don't get race condition for increment
STATIC_BALK_TOTAL = simpy.Resource(env, NUMBER_OF_CUSTOMERS + 1)
DYNAMIC_BALK_TOTAL = simpy.Resource(env, NUMBER_OF_CUSTOMERS + 1)

STATIC_CUSTOMER_COUNT = simpy.Resource(env, NUMBER_OF_CUSTOMERS + 1)
DYNAMIC_CUSTOMER_COUNT = simpy.Resource(env, NUMBER_OF_CUSTOMERS + 1)

# Debug variables:
PRINT_DEBUG_MESSAGES = False
TIME_DEBUGGING = False


def customer_generator(env, number, mean_interarrival_time, lanes, stations, scenario_number):
    """
        Generates customers for both scenarios
    """
    for i in range(number):
        if scenario_number == 1:
            c = customer(env, 'Static Customer%02d' %
                                i, lanes, stations)
            global STATIC_CUSTOMER_COUNT
            STATIC_CUSTOMER_COUNT.request()
        else:
            # This should never happen since the scenario numbers are hard-coded, but just for safety.
            print("An undefined scenario has been requested and cannot be simulated. Please contact the developer.")
            return

        env.process(c)
        interarrival_time = random.expovariate(1.0 / mean_interarrival_time)
        yield env.timeout(interarrival_time)


def customer(env, name, lanes, stations):
    """
        Customer arrives, is served and leaves.
        env - Environment
        name - customer's name
        lanes - array of lanes where:
            0 : order lane
            1 : payment lane
            2 : pickup lane
    """
    if lanes[0].count == lanes[0].capacity:
        # IF THE LINE IS FULL, LEAVEEE
        if PRINT_DEBUG_MESSAGES:
            print("I'm outta here! I don't have time for this!")
        global STATIC_BALK_TOTAL
        STATIC_BALK_TOTAL.request()
        return

    start = env.now
    lane_req = None

    # Occupy a spot in the lane that you picked.
    lane_req = lanes[0].request()

    if PRINT_DEBUG_MESSAGES:
        print("%s chose lane %d" % (name, lane_picked))

    # Get in line for the order station.
    station_req = stations[0].request()

    # Wait until it is your turn to order.
    yield station_req

    if PRINT_DEBUG_MESSAGES:
        print("%s is placing their order at time %d" % (name, env.now))

    # Place your order
    order_time = random.expovariate(1.0 / MEAN_ORDER_TIME)
    if TIME_DEBUGGING:
        print("Order_time: %d" % order_time)

    global TOTAL_ORDER_TIME
    TOTAL_ORDER_TIME += order_time
    yield env.timeout(order_time)

    if PRINT_DEBUG_MESSAGES:
        print("%s has food prep starting at %d" % (name, env.now))

    # Food prep begins NOW
    food_prep_time = random.expovariate(1.0 / MEAN_FOOD_PREP_TIME)
    if TIME_DEBUGGING:
        print("food_prep_time: %d" % food_prep_time)

    global TOTAL_PREP_TIME
    TOTAL_PREP_TIME += food_prep_time
    prep = env.timeout(food_prep_time)
    simpy.events.Event(env).trigger(prep)

    pickup_lane_req = lanes[1].request()

    if PRINT_DEBUG_MESSAGES:
        print("%s is waiting for a spot in the pickup lane" % name)

    yield pickup_lane_req

    # Once you've got a spot in the pickup lane, release your spot in
    # the lane you picked and the order station for that lane
    stations[0].release(station_req)
    lanes[0].release(lane_req)

    if PRINT_DEBUG_MESSAGES:
        print("%s got into the pickup lane and has relinquished their spot in lane %d" %
              (name, 0))
        print("released spot from lane %d, current values of that lane:" %
              0)
        print("lane: %d \t capacity: %d \t count: %d" %
              (0, lanes[0].capacity, lanes[0].count))

    # Request order window resource
    pickup_window_req = stations[2].request()

    yield pickup_window_req

    if PRINT_DEBUG_MESSAGES:
        print("%s is now at the pickup window and is about to pay" % name)

    # Once the resource is acquired, begin payment timeout
    pickup_time = random.expovariate(1.0 / MEAN_PICKUP_TIME)
    if TIME_DEBUGGING:
        print("pickup_time: %d" % pickup_time)
        print("arrived at %d, left at %d, pickup_time: %0.2f" %
              (arrive_at_window, arrive_at_window, pickup_time))

    global TOTAL_PICKUP_TIME
    TOTAL_PICKUP_TIME += pickup_time
    arrive_at_window = env.now
    yield env.timeout(pickup_time) & prep

    stations[2].release(pickup_window_req)
    lanes[2].release(pickup_lane_req)

    if PRINT_DEBUG_MESSAGES:
        print("%s has now paid their bill and received their food" % name)


def run_sim():
    # Get all the globals that we have to modify.
    global MEAN_ORDER_TIME
    global MEAN_PICKUP_TIME

    global STATIC_BALK_TOTAL
    global DYNAMIC_BALK_TOTAL

    global STATIC_CUSTOMER_COUNT
    global DYNAMIC_CUSTOMER_COUNT

    global RUN_TIL

    STATIC_BALK_TOTAL = simpy.Resource(env, NUMBER_OF_CUSTOMERS + 1)
    DYNAMIC_BALK_TOTAL = simpy.Resource(env, NUMBER_OF_CUSTOMERS + 1)

    STATIC_CUSTOMER_COUNT = simpy.Resource(env, NUMBER_OF_CUSTOMERS + 1)
    DYNAMIC_CUSTOMER_COUNT = simpy.Resource(env, NUMBER_OF_CUSTOMERS + 1)

    # Interval vars
    INTERVAL = 180  # Approximately 3 hours if each time unit is a minute
    RUN_TIL += INTERVAL

    # Allocate resources for each initial lane, the order stations, and the second merged lane.
    lane_1 = simpy.Resource(env, 9)  # Order lane
    lane_2 = simpy.Resource(env, 3)  # Payment lane
    lane_3 = simpy.Resource(env, 2)  # Pickup lane

    order_station = simpy.Resource(env)
    pickup_window = simpy.Resource(env)

    # Put lanes into lists for ease of passing around
    lanes = [lane_1, lane_2, lane_3]
    stations = [order_station, pickup_window]

    # Fill the pipeline by running for 3 hours
    env.process(customer_generator(
        env, NUMBER_OF_CUSTOMERS, MEAN_INTERARRIVAL_TIME, lanes, stations, 1))
    env.run(RUN_TIL)

    # Note the starting values for the simulation
    start_cst_cnt = STATIC_CUSTOMER_COUNT.count
    start_blk_cnt = STATIC_BALK_TOTAL.count

    # Set environment variables for the second scenario
    MEAN_ORDER_TIME = 2.0
    MEAN_PICKUP_TIME = 2.0

    print("\nSimulating a MIT of: %0.1f" % MEAN_INTERARRIVAL_TIME)

    s_run_balk = []
    # Start processes and run, fill the pipeline
    while STATIC_CUSTOMER_COUNT.count < NUMBER_OF_CUSTOMERS:
        random.seed(random.random() * 10000000)
        RUN_TIL += INTERVAL

        env.run(RUN_TIL)
        s_run_balk.append((STATIC_CUSTOMER_COUNT.count - start_st_cst_cnt, STATIC_BALK_TOTAL.count))

    # Ensure that there are no more processes to be done.
    env.run()

    # The total number of customers that are accurately simulated
    # after the pipeline is filled.
    static_customers_simulated = NUMBER_OF_CUSTOMERS - start_st_cst_cnt

    # Balking numbers adjusted to remove the balks that occur
    # when the pipeline is being filled.
    adjusted_balk_static = STATIC_BALK_TOTAL.count - start_st_blk_cnt

    # Customer numbers that result from the number of customers that
    # are accurately simulated with their ajusted balk numbers removed.
    adjusted_customers_static = static_customers_simulated - adjusted_balk_static

    s_balk_percentages = [] # List of balk percentage for each run
    last_cust_total = 0
    for pair in s_run_balk:
        # Each pair within this list is comprised of the number of the number of customers served
        # at the end of the time period and the number of balks at the end of the time period
        s_balk_percentages.append(float(pair[1]) / float(pair[0] - last_cust_total))
        last_cust_total = pair[0]


    s_balk_avg = sum(s_balk_percentages) / len(s_balk_percentages)
    print(statistics.variance(s_balk_percentages))

    print("\nOVERALL STATIC STATISTICS:")
    print('{0: <28}{1: <5}\n{2: <28}{3: <5}\n{4: <28}{5: <5}\n{6: <28}{7: <5}\n{8: <28}{9: <5}\n'.format(\
            "Customers Simulated:", "%d" % static_customers_simulated,\
            "Customers Served:", "%d" % adjusted_customers_static, \
            "Balk total:", "%d" % STATIC_BALK_TOTAL.count,\
            "Static average balk rate:", "%0.2f%%" % s_balk_avg,\
            "Variance of balk rate:", "%0.2f%%" % statistics.variance(s_balk_percentages)))


for i in range(15):
    run_sim()
    MEAN_INTERARRIVAL_TIME -= 0.2

print("FINISHED")
