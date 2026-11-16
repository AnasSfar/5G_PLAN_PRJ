# Project transcript
_Source: C-RAN work_instructions_v2.pdf — 3 slides_

## Slide 1

PROJECT INSTRUCTIONS 
You can select the programming language (C++, Matlab, C#, Python…) you feel more 
comfortable with.  
You have to work in teams of three students, individual projects will not be accepted. All the 
teams work on the same project, but of course you will arrive to different solutions because the 
scenario will be different. 
 
PROJECT OBJECTIVES 
To face a Cloud Radio Access Network design, optimizing the number of BBUpools and RRHs to 
satisfy: maximum delays that are acceptable, as well as load and traffic balancing. 
To do so, you have to read the document uploaded (master thesis) trying to reproduce it. The 
scenario can be different (any geographical area can be used). If you can get realistic information 
about sites (coming from a mobile operator) results will be more applicable. If not, you can use 
a synthetic scenario (a region of 30 x 30 km where you deploy the RRHs and possible BBUpool 
locations randomly but with some restrictions about minimum distance between two RRHs and 
minimum distance between two BBU pools). 
Laboratory class is C4-333G, but of course you can use your own laptop. You can access the lab 
when you wish except when the lab is used by other professors (the schedule is at the lab door). 
Additionally you have to do a link budget for your 5G deployment, in an Excel file.  
 
 FINAL AVALUATION 
You have to write a report with your main conclusions about the simulation, showing figures 
diagrams etc that allow to compare the different balance techniques. During the project you will 
have to write weekly intermediate reports showing your progress, so the final report is the 
combination of these, adding last simulations, their analysis and conclusions. 
You have to demonstrate that your software is running by showing it in class, main input 
parameters, variables, algorithms, results etc. You have to prepare and print a poster with your 
main achievements, explaining the poster in class. Questions about the project will be asked by 
other teams and by myself, during this presentation. 
So the evaluation will be based on: intermediate reports, final report, poster quality and 
presentation, capacity of answering the proposed questions, quality of the work done and 
motivation. 
 
FIRST WEEK: SCENARIO DEFINITION 
A 30 x 30 km (aprox) should be used. Select a region where you are sure that can find information 
about the real eNB deployed.  
Some references that can be useful: 
Ministerio para la transformación digital y de la función pública, “Infoantenas”.

## Slide 2

Available: https://geoportal.minetur.gob.es/VCTEL/vcne.do. 
https://datos.gob.es/es/aplicaciones/antenas-de-telefonia-movil-2g-3g-4g-y-5g 
 
 
Open database of Cell Towers & Geolocation. OpenCelliD 
https://opencelid.org/OpenCelliD  
https://opencellid.org/#zoom=10&lat=41.678&lon=-0.887 
 
Antenas gsm - Mapa de antenas Telefonía Móvil para comprobar La Cobertura Móvil 
2G,3G, 4G y 5g con ubicaciones y bandas. AntenasGSM.com. 
https://antenasgsm.com/41.63379452793018/-
0.8763069056356017/9.51881399757081/true,true,true,true,true 
 
Infoantenas. Niveles de Exposición. 
https://geoportal.minetur.gob.es/VCTEL/vcne.do 
 
Cobertura Orange 5G en España - Mapa de Cobertura móvil (n.d.). 
https://www.orange.es/5g 
 
Cobertura móvil 2G, 3G, 4G y 5G. Mapa Cobertura - Movistar (n.d). 
https://www.movistar.es/particulares/coberturas/movil/ 
 
Consultar el mapa de cobertura movil 5G, 4G+, 4G, 3G o 2G (n.d). 
https://www.vodafone.es/c/conocenos/es/vodafone-espana/mapa-cobertura-movil/ 
 
Cobertura móvil 5G - MÁSMÓVIL. (n.d). https://www.masmovil.es/cobertura-movil 
 
Mapa de Cobertura 3G / 4G / 5G Movistar Movil. Cobertura 3G / 4G / 5G Movistar Movil 
nPerf.com. (n.d.). 
https://www.nperf.com/es/map/ES/-/168910.Movistar-
Movil/signal/?ll=41.54661683829194&lg=-0.8562564529362994&zoom=10 
 
 
Particularly, reference 1 (infoantenas) is very useful. This is controlled by the Secretaria de 
Estado para la Sociedad de la Información y la Agenda Digital, an official government body 
responsible for publishing national telecommunication infrastructure data. This online portal 
provides an interactive interface that visualizes cellular base stations and related network 
elements across Spain. Each site entry typically includes operator information, geographic 
coordinates, and supported technologies (2G, 3G, 4G and 5G). 
Additionally, clicking on one of the base stations takes you to a page which provides details 
about operating frequency bands, network operator and measured electromagnetic field levels 
in the surrounding area. 
The problem is that Infoantenas data is not easily parsable into a clean dataset, but you can use 
a web scraper to do so. The web scraper can collect base station data by calling Infoantenas 
through its GeoJSON API, obtaining clean, structured data and avoiding parsing the webpage. 
The script divides the study area into tiles, queries each tile, and extracts the data: site ID, 
coordinates, operator, and supported technologies.  
After collecting the raw entries, you can run a small set of processing steps to prepare the data 
set. For example: filtering the sites that do not support 4G or 5G, adding labels indicating

## Slide 3

whether a site supports 4G, 5G, or both, etc. At the end you have to obtain a clean and useful 
dataset, easy to map, and use in the C-RAN simulator. The data set can be stored in .json format 
or other formats, but JSON structure facilitates conversion to other formats as well as CSV for 
visualisation and statistical analysis, using for example the Folium package with Python. 
SYNTHETIC RRU AND INITIAL BBUpooL ASSIGNEMENT 
To support robustness testing, the program should also allow to inject additional synthetic RRHs. 
These are placed uniformly at random inside the scenario bounding box and clearly labelled so 
they do not interfere with the real sites during interpretation. This helps verify behaviour when 
density increases and ensures the assignment logic remains correct. The number of synthetic 
RRHs should be a variable in the software. 
BBUpool number and position. Consider that every RRH location is a potential BBU pool location. 
The number of BBUpools should be a variable to facilitate the comparison for different 
assumptions. In the algorithm you can consider every RRH as a candidate set and select K 
BBUpools using and heuristic software (farthest-first k-center, etc.). This will spread the pools 
across the region reducing the maximum distance between any RRH and its nearest pool. After 
analysing the results for different K values, you can select the number and position of the 
BBUpools more adequate to your scenario. 
REPORT 
With explanations, references, figures and the analysis and comments for the obtained results.
