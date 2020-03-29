import random
import simpy


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

# Make these be resources so we don't get race condition for increment
STATIC_BALK_TOTAL = simpy.Resource(env, NUMBER_OF_CUSTOMERS + 1)
DYNAMIC_BALK_TOTAL = simpy.Resource(env, NUMBER_OF_CUSTOMERS + 1)

STATIC_CUSTOMER_COUNT = simpy.Resource(env, NUMBER_OF_CUSTOMERS + 1)
DYNAMIC_CUSTOMER_COUNT = simpy.Resource(env, NUMBER_OF_CUSTOMERS + 1)

# Debug variables:
PRINT_DEBUG_MESSAGES = False
TIME_DEBUGGING = False

CUSTOMER_TOTAL_TIME = []


def customer_generator(env, number, mean_interarrival_time, lanes, stations, scenario_number):
    """
        Generates customers for both scenarios
    """
    for i in range(number):
        if scenario_number == 1:
            c = customer_static(env, 'Static Customer%02d' %
                                i, lanes, stations)
            global STATIC_CUSTOMER_COUNT
            STATIC_CUSTOMER_COUNT.request()
        elif scenario_number == 2:
            c = customer_dynamic(env, 'Dynamic Customer%02d' %
                                 i, lanes, stations)
            global DYNAMIC_CUSTOMER_COUNT
            DYNAMIC_CUSTOMER_COUNT.request()
        else:
            # This should never happen since the scenario numbers are hard-coded, but just for safety.
            print("An undefined scenario has been requested and cannot be simulated. Please contact the developer.")
            return

        env.process(c)
        interarrival_time = random.expovariate(1.0 / mean_interarrival_time)
        yield env.timeout(interarrival_time)


def customer_static(env, name, lanes, stations):
    """Customer arrives, is served and leaves."""
    if lanes[0].count == lanes[0].capacity and lanes[1].count == lanes[1].capacity:
        # IF BOTH LINES ARE FULL, LEAVEEE
        if PRINT_DEBUG_MESSAGES:
            print("I'm outta here! I don't have time for this!")
        global STATIC_BALK_TOTAL
        STATIC_BALK_TOTAL.request()
        return

    start = env.now
    lane_req = None
    lane_picked = 0

    if lanes[1].count < lanes[0].count:
        # The customer will choose the lane with the least number of people in it.
        lane_picked = 1

    # Occupy a spot in the lane that you picked.
    lane_req = lanes[lane_picked].request()

    if PRINT_DEBUG_MESSAGES:
        print("%s chose lane %d" % (name, lane_picked))

    # Get in line for the order station.
    station_req = stations[lane_picked].request()

    # Wait until it is your turn to order.
    yield station_req

    if PRINT_DEBUG_MESSAGES:
        print("%s is placing their order at time %d" % (name, env.now))

    # Place your order
    order_time = random.expovariate(1.0 / MEAN_ORDER_TIME)
    if TIME_DEBUGGING:
        print("Order_time: %d" % order_time)

    yield env.timeout(order_time)

    if PRINT_DEBUG_MESSAGES:
        print("%s has food prep starting at %d" % (name, env.now))

    # Food prep begins NOW
    food_prep_time = random.expovariate(1.0 / MEAN_FOOD_PREP_TIME)
    if TIME_DEBUGGING:
        print("food_prep_time: %d" % food_prep_time)

    prep = env.timeout(food_prep_time)
    simpy.events.Event(env).trigger(prep)

    pickup_lane_req = lanes[2].request()

    if PRINT_DEBUG_MESSAGES:
        print("%s is waiting for a spot in the pickup lane" % name)

    yield pickup_lane_req

    # Once you've got a spot in the pickup lane, release your spot in
    # the lane you picked and the order station for that lane
    stations[lane_picked].release(station_req)
    lanes[lane_picked].release(lane_req)

    if PRINT_DEBUG_MESSAGES:
        print("%s got into the pickup lane and has relinquished their spot in lane %d" %
              (name, lane_picked))
        print("released spot from lane %d, current values of that lane:" %
              lane_picked)
        print("lane: %d \t capacity: %d \t count: %d" %
              (lane_picked, lanes[lane_picked].capacity, lanes[lane_picked].count))

    # Request order window resource
    pickup_window_req = stations[2].request()

    yield pickup_window_req

    if PRINT_DEBUG_MESSAGES:
        print("%s is now at the pickup window and is about to pay" % name)

    # Once the resource is acquired, begin payment timeout
    pickup_time = random.expovariate(1.0 / MEAN_PICKUP_TIME)
    if TIME_DEBUGGING:
        print("pickup_time: %d" % pickup_time)

    yield env.timeout(pickup_time) & prep

    stations[2].release(pickup_window_req)
    lanes[2].release(pickup_lane_req)

    CUSTOMER_TOTAL_TIME.append(env.now - start)

    if PRINT_DEBUG_MESSAGES:
        print("%s has now paid their bill and received their food" % name)


def customer_dynamic(env, name, lanes, stations):
    """Customer arrives, is served and leaves."""
    if lanes[0].count == lanes[0].capacity and lanes[1].count == lanes[1].capacity:
        # IF BOTH LINES ARE FULL, LEAVEEE
        if PRINT_DEBUG_MESSAGES:
            print("I'm outta here! I don't have time for this!")
        global DYNAMIC_BALK_TOTAL
        DYNAMIC_BALK_TOTAL.request()
        return

    start = env.now
    lane_req = None
    lane_picked = 0

    if lanes[1].count < lanes[0].count:
        # The customer will choose the lane with the least number of people in it.
        lane_picked = 1

    # Occupy a spot in the lane that you picked.
    lane_req = lanes[lane_picked].request()

    if PRINT_DEBUG_MESSAGES:
        print("%s chose lane %d" % (name, lane_picked))

    # Get in line for the order station.
    station_req = stations[lane_picked].request()

    # Wait until it is your turn to order.
    yield station_req

    if PRINT_DEBUG_MESSAGES:
        print("%s just got the order-server at  %d" % (name, env.now))

    # Place your order
    order_time = random.expovariate(1.0 / MEAN_ORDER_TIME)
    if TIME_DEBUGGING:
        print("Order_time: %d" % order_time)

    yield env.timeout(order_time)

    if PRINT_DEBUG_MESSAGES:
        print("%s has food prep starting at %d" % (name, env.now))

    # Release the empoloyee that is taking your order but stay in line.
    stations[lane_picked].release(station_req)
    if PRINT_DEBUG_MESSAGES:
        print("%s has released the server at time %d" % (name, env.now))

    # Food prep begins NOW
    food_prep_time = random.expovariate(1.0 / MEAN_FOOD_PREP_TIME)
    if TIME_DEBUGGING:
        print("food_prep_time: %d" % food_prep_time)

    prep = env.timeout(food_prep_time)
    simpy.events.Event(env).trigger(prep)

    pickup_lane_req = lanes[2].request()

    if PRINT_DEBUG_MESSAGES:
        print("%s is waiting for a spot in the pickup lane" % name)

    yield pickup_lane_req

    # Once you've got a spot in the pickup lane, release your spot in
    # the lane you picked.
    lanes[lane_picked].release(lane_req)
    # Request order window resource
    pickup_window_req = stations[2].request()

    if PRINT_DEBUG_MESSAGES:
        print("released spot from lane %d, current values of that lane:" %
              lane_picked)
        print("lane: %d \t capacity: %d \t count: %d" %
              (lane_picked, lanes[lane_picked].capacity, lanes[lane_picked].count))

        print("%s got into the pickup lane and has relinquished their spot in lane %d" %
              (name, lane_picked))

    yield pickup_window_req

    if PRINT_DEBUG_MESSAGES:
        print("%s is now at the pickup window and is about to pay" % name)

    # Once the resource is acquired, begin payment timeout
    pickup_time = random.expovariate(1.0 / MEAN_PICKUP_TIME)
    if TIME_DEBUGGING:
        print("pickup_time: %d" % pickup_time)

    yield env.timeout(pickup_time) & prep

    stations[2].release(pickup_window_req)
    lanes[2].release(pickup_lane_req)

    CUSTOMER_TOTAL_TIME.append(env.now - start)

    if PRINT_DEBUG_MESSAGES:
        print("%s has now paid their bill and received their food at time %d" %
              (name, env.now))


def run_sim():
    # Get all the globals that we have to modify.
    global MEAN_ORDER_TIME
    global MEAN_PICKUP_TIME

    global STATIC_BALK_TOTAL
    global DYNAMIC_BALK_TOTAL

    global STATIC_CUSTOMER_COUNT
    global DYNAMIC_CUSTOMER_COUNT

    global RUN_TIL
    global CUSTOMER_TOTAL_TIME 

    # Keeps track of how long each customer is in the line
    CUSTOMER_TOTAL_TIME = []

    STATIC_BALK_TOTAL = simpy.Resource(env, NUMBER_OF_CUSTOMERS + 1)
    DYNAMIC_BALK_TOTAL = simpy.Resource(env, NUMBER_OF_CUSTOMERS + 1)

    STATIC_CUSTOMER_COUNT = simpy.Resource(env, NUMBER_OF_CUSTOMERS + 1)
    DYNAMIC_CUSTOMER_COUNT = simpy.Resource(env, NUMBER_OF_CUSTOMERS + 1)

    # Interval vars
    INTERVAL = 180  # Approximately 3 hours if each time unit is a minute
    RUN_TIL += INTERVAL

    # Allocate resources for each initial lane, the order stations, and the second merged lane.
    lane_1a = simpy.Resource(env, 5)  # First order lane
    lane_1b = simpy.Resource(env, 5)  # Second order lane
    lane_2 = simpy.Resource(env, 7)  # Pickup lane

    lane_1a_order_station = simpy.Resource(env)
    lane_1b_order_station = simpy.Resource(env)
    pickup_window = simpy.Resource(env)

    # Put lanes into lists for ease of passing around
    lanes = [lane_1a, lane_1b, lane_2]
    stations = [lane_1a_order_station, lane_1b_order_station, pickup_window]

    # Fill the pipeline by running for 3 hours
    env.process(customer_generator(
        env, NUMBER_OF_CUSTOMERS, MEAN_INTERARRIVAL_TIME, lanes, stations, 1))
    env.run(RUN_TIL)

    # Note the starting values for the simulation
    start_st_cst_cnt = STATIC_CUSTOMER_COUNT.count
    start_st_blk_cnt = STATIC_BALK_TOTAL.count

    # Set environment variables for the second scenario
    MEAN_ORDER_TIME = 2.0
    MEAN_PICKUP_TIME = 2.0

    print("\nSimulating a MIT of: %0.1f" % MEAN_INTERARRIVAL_TIME)

    s_run_balk = []

    last_balk_cnt = 0
    last_cst_cnt = start_st_cst_cnt
    # Start processes and run, fill the pipeline
    while STATIC_CUSTOMER_COUNT.count < NUMBER_OF_CUSTOMERS:
        random.seed(random.random() * 10000000)
        RUN_TIL += INTERVAL

        env.run(RUN_TIL)
        # Append (number of customers simulated, number that balked)
        s_run_balk.append((STATIC_CUSTOMER_COUNT.count - last_cst_cnt, STATIC_BALK_TOTAL.count - last_balk_cnt))

        # Since the two resources below are cumulative, keep track of
        # how much has changed since the last run
        last_balk_cnt = STATIC_BALK_TOTAL.count
        last_cst_cnt = STATIC_CUSTOMER_COUNT.count

    s_avg_cust_time = sum(CUSTOMER_TOTAL_TIME) / len(CUSTOMER_TOTAL_TIME)
    # Clear the list
    CUSTOMER_TOTAL_TIME = []
    # Ensure that there are no more processes to be done.
    env.run()

    RUN_TIL = env.now
    RUN_TIL += INTERVAL

    # Fill the pipeline by running for 3 hours
    env.process(customer_generator(
        env, NUMBER_OF_CUSTOMERS, MEAN_INTERARRIVAL_TIME, lanes, stations, 2))
    env.run(RUN_TIL)

    # Note values at start of simulation
    start_dy_cst_cnt = DYNAMIC_CUSTOMER_COUNT.count
    start_dy_blk_cnt = DYNAMIC_BALK_TOTAL.count

    # Set environment variables for the second scenario
    MEAN_ORDER_TIME = 1.5
    MEAN_PICKUP_TIME = 1.0

    d_run_balk = []
    last_balk_cnt = 0
    last_cst_cnt = start_dy_cst_cnt
    # Start processes and run, fill the pipeline
    while DYNAMIC_CUSTOMER_COUNT.count < NUMBER_OF_CUSTOMERS:
        random.seed(random.random() * 10000000)
        RUN_TIL += INTERVAL

        env.run(RUN_TIL)
        # Append (number of customers simulated, number that balked)
        d_run_balk.append((DYNAMIC_CUSTOMER_COUNT.count - last_cst_cnt, DYNAMIC_BALK_TOTAL.count - last_balk_cnt))

        # Since the two resources below are cumulative, keep track of
        # how much has changed since the last run
        last_balk_cnt = DYNAMIC_BALK_TOTAL.count
        last_cst_cnt = DYNAMIC_CUSTOMER_COUNT.count

    d_avg_cust_time = sum(CUSTOMER_TOTAL_TIME) / len(CUSTOMER_TOTAL_TIME)
    env.run()

    # The total number of customers that are accurately simulated
    # after the pipeline is filled.
    static_customers_simulated = NUMBER_OF_CUSTOMERS - start_st_cst_cnt
    dynamic_customers_simulated = NUMBER_OF_CUSTOMERS - start_dy_cst_cnt

    # Balking numbers adjusted to remove the balks that occur
    # when the pipeline is being filled.
    adjusted_balk_static = STATIC_BALK_TOTAL.count - start_st_blk_cnt
    adjusted_balk_dynamic = DYNAMIC_BALK_TOTAL.count - start_dy_blk_cnt

    # Customer numbers that result from the number of customers that
    # are accurately simulated with their ajusted balk numbers removed.
    adjusted_customers_static = static_customers_simulated - adjusted_balk_static
    adjusted_customers_dynamic = dynamic_customers_simulated - adjusted_balk_dynamic

    s_balk_percentages = [] # List of balk percentage for each run
    s_cust_served_per_run = []
    for pair in s_run_balk:
        # Each pair within this list is comprised of the number of the number of customers simulated
        # at the end of the time period and the number of balks at the end of the time period
        s_balk_percentages.append(float(pair[1]) / float(pair[0]))
        s_cust_served_per_run.append(pair[0] - pair[1])

    s_cust_per_run_avg = float(sum(s_cust_served_per_run)) / float(len(s_cust_served_per_run))
    s_balk_avg = sum(s_balk_percentages) / len(s_balk_percentages)

    d_balk_percentages = [] # List of balk percentage for each run
    d_cust_served_per_run = []
    for pair in d_run_balk:
        # Each pair is (no_of_customers, no_of_balks)
        d_balk_percentages.append(float(pair[1]) / float(pair[0]))
        # Get number of customers served in this run
        d_cust_served_per_run.append(pair[0] - pair[1])

    d_cust_per_run_avg = float(sum(d_cust_served_per_run)) / float(len(d_cust_served_per_run))
    d_balk_avg = sum(d_balk_percentages) / len(d_balk_percentages)

    print("\nOVERALL STATIC STATISTICS:")
    print('{0: <28}{1: <5}\n{2: <28}{3: <5}\n{4: <28}{5: <5}\n{6: <28}{7: <5}'.format(\
            "Customers Simulated:", "%d" % static_customers_simulated,\
            "Customers Served:", "%d" % adjusted_customers_static, \
            "Balk total:", "%d" % STATIC_BALK_TOTAL.count,\
            "Static average balk rate:", "%0.2f%%" % (s_balk_avg * 100.0)))
    print("Average time spent in line: %0.2f" % s_avg_cust_time)
    print("Average customers served per run: %0.2f" % s_cust_per_run_avg)

    print("\nOVERALL DYNAMIC STATISTICS:")
    print('{0: <28}{1: <5}\n{2: <28}{3: <5}\n{4: <28}{5: <5}\n{6: <28}{7: <5}'.format(\
            "Customers Simulated:", "%d" % dynamic_customers_simulated,\
            "Customers Served:", "%d" % adjusted_customers_dynamic,\
            "Balk total:", "%d" % DYNAMIC_BALK_TOTAL.count,\
            "Dynamic average balk rate:", "%0.2f%%" % (d_balk_avg * 100.0)))

    print("Average time spent in line: %0.2f" % d_avg_cust_time)
    print("Average customers served per run: %0.2f" % d_cust_per_run_avg)

while MEAN_INTERARRIVAL_TIME > 0:
    run_sim()
    MEAN_INTERARRIVAL_TIME -= 0.2

print("FINISHED")
