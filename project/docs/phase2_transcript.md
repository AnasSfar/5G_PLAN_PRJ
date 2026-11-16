# Phase 2 transcript
_Source: Project review_phase2_RRH_balancing_and_load_balancing.pdf, 2 pages_

## Page 1

Project review: 
LOAD BALANCING 
Use the pools to make a balanced distribution of RRHs, so the network becomes more resilient 
to faults. The analysis should be done in a virtualised scenario where the load in MBph or in 
GOPS is considered, to balance the number of processing cards required in each pool. There is 
no limit in the maximum number of processing cards that can be installed at the BBUpool (so 
there is no maximum BBUpool capacity); the objective is not minimising the number, but to 
balance the load. 
To do this, the time instant in which the load is balanced should be chosen. Also traffic 
patterns should have been assigned to RRH (residential, office, mixed) and the figure 
characterising each traffic profile for 24 h should be given. 
How does the algorithm work: 
a. Select the hour (8:00, 15:00 (peak) or 21:00) where the analysis will be done. You 
could select the hour when the sum of the three traffics (three type of cells) is 
maximum (usually at noon or close to noon). 
b. First iteration: assign the RRHs that can only be connected to a BBUpool. Calculate the 
load of the BBUpool. 
c. Second iteration: it is crucial how you order the RRHs to be attended, it could happens 
that you find a solution that is not physically implementable. Parameters to be taken 
into account: number of possible connections, distance of these connections, BBUpool 
traffic.  
d. Once a RRH is assigned update the load of the BBUpool and continue until all RRHs 
have been assigned. 
To compare with the balance implemented only in terms of RRHs number per BBUpool.  
e. After step b. Third iteration: sort the remaining RRHs according to their list of possible 
BBUpool connections (in ascending order).  
f. Start assigning RRHs to the BBUpool (from the possible list) that has less RRHs 
allocated to it. Update the number of connections and continue until all RRHs have 
been assigned. 
 
Outputs that should be simulated and represented: 
1. Before running the algorithm (will be useful to compare later with the optimisation). 
a. Load distribution. Before applying any algorithm, with the output of the delay 
algorithm represent the load per BBUpool at 8:00, 15:00 and 21:00 (three 
different figures). The figure should have in the horizontal axis the BBUpool 
identifier, and in the vertical the total load in MBph or in GOPS. 
b. Check what changes if all the RRHs are residential, or if all of them are office 
(representing in a figure 3 columns for each BBU: all residential, all office, real 
case). At least for peak traffic. 
c. Represent the overall network load during day (similar to figure 4.21 in master 
thesis) 
2. After running the algorithm:

## Page 2

a. Figure with the number of RRHs per BBUpool (useful to compare this with the 
assignment done when only delay is considered) 
i. When traffic is considered 
ii. When the number of connexions is considered 
b. Figure or table indicating how many RRHs change its assignment depending on 
the hour. As this is not possible physically, the peak hour should be considered 
as the real adopted case. 
c. Figures comparing the results of balancing when all RRHs are residential or 
office.  
d. Represent a figure similar to fig4.3 in master thesis, where for each distance 
portion (0-1, 1-2, etc) the number of RRHs allocated is represented for the 
three optimisation cases: only distance, load balancing according to traffic, 
load balancing according number of RRHs. 
e. Represent a figure similar to 4.4 in master thesis with the average capacity per 
BBUpool for the three optimisation cases: only distance, load balancing 
according to traffic, load balancing according number of RRHs. 
 
REMEMBER THAT ALL THE ANALYSIS CAN BE DONE WITH A DIFFERENT NUMBER OF BBUpools, 
so when finishing all the algorithms some comparison should be done for three cases (normal, 
few BBUpools, too many BBUpools).
