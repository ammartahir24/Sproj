import os
import codecs
from timeit import default_timer as timer
'''
	Input 1: SSIM transformations:
		Inputs : Webpage URL, list of compressions to apply, boolean variable to specify should image be removed or not
		Example : "localhost:8888/index.html" , [25,50,75,90], remove = True
		Output : Directory where images are stored, Mappings of Compression -> SSIM for each image in webpage (n x d matrix n = number of images, d = number of compressions)
		Example : Directory: "D:/webpage/images"
			Mappings: 
					25	,	50	,	75	,	90	,	removal
			img_1	0.8	,	0.85,	0.9	,	0.95,	0.5
			img_2	0.7	,	0.8,	0.85,	0.9,	0.5

	Input 2: PLT info corresponding to each Transformation:
		Inputs : Directory where images are stored, Mapping matrix (SSIM transformations' output)
		Outputs : Mappings of PLT, CPU time, GPU time for each compression of each image (n x d x 3 matrix)
		Example : 
			Mappings:
							25				,		50				,		75				,		90				,		removal
			img_1		0.8,[2.5,1.3,0.6]	,	0.85,[4.5,3.2,1.2]	,	0.9,[4,2.3,1.1]		,	0.95,[2.3,1.2,0.4]	,		0.5,[0,0,0]
	Input 3: Complete dependency graph (extracted from Wprof and processed):
		Inputs : Webpage URL
		Output : A graph with each node with these attributes: parent node, trigger time, completion time (or total time taken), list of children nodes ordered by trigger times
		Example:
			{...
			html_2 : {
				ID : html_2,
				parent : html_1,
				trigger : 2019,09,29,18:16:48
				completed : 2019,09,29,18:17:02
				children : [(img_4,2019,09,29,18:16:50),(img_5,2019,09,29,18:16:53),(script_1,2019,09,29,18:16:55)]
			}
			...}
	Input 4: Budget (float value)
		Example : 15.0
	Output : List of Optimal compressions for each object on page
		Example :
		{
			html_1 : 100,
			img_1 : 100,
			img_2 : 90,
			img_3 : 25,
			script_1 : 100,
			img_4 : 0
		}
'''

'''
	Test case
'''

DGraph = {
	'html_1' : {
	'ID' : 'html_1',
	'parent' : '',
	'trigger' : 0,
	'completed' : 3200,
	'children' : ['img_1', 'img_2', 'img_3']
	},
	'img_1' : {
	'ID' : 'img_1',
	'parent' : 'html_1',
	'trigger' : 1570,
	'completed' : 4070,
	'children' : []
	},
	'img_2' : {
	'ID' : 'img_2',
	'parent' : 'html_1',
	'trigger' : 1710,
	'completed' : 3205,
	'children' : []
	},
	'img_3' : {
	'ID' : 'img_3',
	'parent' : 'html_1',
	'trigger' : 1850,
	'completed' : 5350,
	'children' : []
	}
}



SSIMs = {
	"img_1" : {'keys' : ['img_1_0','img_1_25','img_1_50','img_1_75','img_1'], 'img_1_0' : (0.65, 1), 'img_1_25' : (0.71, 0.89), 'img_1_50' : (0.77,0.85), 'img_1_75' : (0.83, 0.79), 'img_1' :(1.0,0)},
	"img_2" : {'keys' : ['img_2_0','img_2_25','img_2_50','img_2_75','img_2'], 'img_2_0' : (0.79, 1), 'img_2_25' : (0.86, 0.91), 'img_2_50' : (0.94,0.84), 'img_2_75' : (0.96, 0.78), 'img_2' :(1.0,0)},
	"img_3" : {'keys' : ['img_3_0','img_3_25','img_3_50','img_3_75','img_3'], 'img_3_0' : (0.75, 1), 'img_3_25' : (0.84, 0.84), 'img_3_50' : (0.91,0.79), 'img_3_75' : (0.96, 0.66), 'img_3' :(1.0,0)}
}


def Concat_and_Update(trans_lists, new_trans, SSIM):
	'''
		Finds cummulative ssim values and merges multiple lists into one list
	'''
	transformations = [new_trans]
	for tl in trans_lists:
		for each in tl:
			transformations.append(each)
	SSIM = sum([x[2] for x in transformations]) + 1 - len(transformations)
	return transformations, SSIM


def Dynamic_Sol(n, dep_graph, mappings, budget, SSIM):
	'''
		returns list of transformations of the node and its children
	'''
	node = dep_graph[n]

	'''
		If budget is less than 0, no solution possible
	'''
	if budget < 0:
		return -1

	max_SSIM , best_transformation = -1 , []
	if ('src' not in node) or ('image' not in node['mimeType']):
		thisMap = {'keys' : [node['ID']], node['ID'] : (1,0)}
	else:
		srckey = node['src'].split('/')[-1]
		thisMap = mappings[srckey]

	'''
		if no children return most optimal value: 
			objects returned: object_ID, transformation, SSIM (e.g. ("img_1", "img_1_50", 0.85))
	'''
	if not len(node['children']):
		maxSSIM , key = -1, -1
		for index in thisMap['keys']:
			t = thisMap[index]
			if maxSSIM < t[0] and ((node['completed']-node['trigger']) - t[1]*(node['completed']-node['trigger'])) < budget:
				maxSSIM , key = t[0] , index
		if maxSSIM == -1: return -1
		return [(n , key, maxSSIM)]

	'''
		If object has children, it must be an html type node which does not have multiple states. Therefore, if budget is smaller than its completion time, no solution is possible
	'''
	if budget < (node['completed'] - node['trigger']) : return -1

	'''
		If object has children and satisfies budget constraint. recur, concatenate and return results
	'''

	for index in thisMap["keys"]:
		t = thisMap[index]
		sub_transformations = []
		for child in node['children']:
			child = child[0]
			child_res = Dynamic_Sol(child, dep_graph, mappings, budget-(dep_graph[child]['trigger'] - dep_graph[n]['trigger']), SSIM)
			if child_res != -1:
				sub_transformations.append(child_res)
		sub_transformations, temp_SSIM = Concat_and_Update(sub_transformations,(n, index, t[0]), t[0])
		if temp_SSIM > max_SSIM:
			max_SSIM, best_transformation = temp_SSIM, sub_transformations
	if max_SSIM == -1: return -1
	return best_transformation



'''
	To be used as an interface, once all work is completed
'''

# from wm_ssim import SSIM_transformations
# from wprof_util import Dependency_Graph
# from time_mappings import Times

def Optimize(web, budget):
	directory,mappings = SSIM_transformations(web)
	mappings = Times(directory,mappings)
	dep_graph = Dependency_Graph(web)
	solution = Dynamic_Sol(dep_graph[0], mappings, budget, 1)
	if solution == -1 : return "No solution, Budget too small"
	SSIM = sum([x[2] for x in solution]) + 1 - len(solution)
	return solution

import json
import csv

imgDB = {}

def readfrom(file):
	with open(file,'r') as json_file:
		data = json.load(json_file)
		return data


def buildImgDB(file):
	global imgDB
	with open(file) as csv_file:
		csv_reader = csv.reader(csv_file,delimiter=',')
		for record in csv_reader:
			imgDB[record[1]+'_'+record[0]] = float(record[3])

# print imgDB


buildImgDB('sampled_10_images_compression_matrix.csv')
dep = readfrom('3o.json')
ssims = readfrom('ssim3.json')
transformation = {}
compressions = [25,50,75,0]
for _,value in ssims.iteritems():
	src = value['src']
	t_here = {}
	t_here['keys'] = []
	for c in compressions:
		if c==0:
			t_here[str(c)+'_'+src] = (value['remove'], 1)
			t_here['keys'] += [str(c)+'_'+src]
		elif value['compress'+'_'+str(c)] != -1:
			t_here[str(c)+'_'+src] = (value['compress'+'_'+str(c)], (imgDB[str(c)+'_'+src])/100)
			t_here['keys'] += [str(c)+'_'+src]
	t_here[src] = (1,0)
	t_here['keys'] += [src]
	transformation[src] = t_here

start = timer()
solution = Dynamic_Sol('Networking_0', dep, transformation, 550, 1)
end = timer()
timeElapsed = end - start
print "Time:", timeElapsed
if solution == -1:
	print "No solution, Budget too small"
else:
	SSIM = sum([x[2] for x in solution]) + 1 - len(solution)
	print "SSIM:", SSIM
	print "Mappings:"
	print solution


# from bs4 import BeautifulSoup

# def GenerateHTML(content, mappings):
# 	soup = BeautifulSoup(content, 'html.parser')
# 	imgs = soup.find_all('img')
# 	for img in imgs:
# 		print img['src']
# 		print '\n'
# 		imgname = img['src'].split('/')[-1]
# 		imgext = imgname.split('.')[1]
# 		oldimglen = len(imgname)
# 		for j in mappings:
# 			if j[0] == imgname.split('.')[0]:
# 				imgname = j[1]+'.'+imgext
# 		img['src'] = img['src'][:-1*(oldimglen)]+imgname
# 		print img['src']
# 	return soup

# file = codecs.open("index.html","rb")
# content = str(file.read())
# s = str(GenerateHTML(content, solution))
# wfile = codecs.open("index_o.html","wb")
# wfile.write(s)

