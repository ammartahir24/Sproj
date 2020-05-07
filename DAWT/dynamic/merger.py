import json
import csv

imgDB = {}

def readfrom(file):
	with open(file,'r') as json_file:
		data = json.load(json_file)
		return data

# print readfrom('3o.json')

def buildImgDB(file):
	global imgDB
	with open(file) as csv_file:
		csv_reader = csv.reader(csv_file,delimiter=',')
		for record in csv_reader:
			imgDB[record[1]+'_'+record[0]] = float(record[3])

buildImgDB('sampled_10_images_compression_matrix.csv')
# print imgDB


ssims = readfrom('ssim3.json')
transformation = {}
compressions = [25,50,75,0]
for _,value in ssims.iteritems():
	src = value['src']
	t_here = {}
	t_here['keys'] = []
	for c in compressions:
		if c==0:
			t_here[str(c)+'_'+src] = (value['remove'], (imgDB[str(c)+'_'+src])/100)
		else:
			t_here[str(c)+'_'+src] = (value['compress'+'_'+str(c)], (imgDB[str(c)+'_'+src])/100)
		t_here['keys'] += [str(c)+'_'+src]
	t_here[src] = (1,0)
	t_here['keys'] += [src]
	transformation[src] = t_here
print transformation