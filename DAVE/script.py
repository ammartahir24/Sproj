import timeit
import os
import time
import numpy as np
import csv

inputfile = 'input'
input_extension = '.mp4'
default_fps = 30
default_bitrate = 2500
default_res = 480
running = False
prevFrame = 0
filename = ""
renderedFPS = []
wait = 0

def configuration():
	config_file = open('config.txt', 'r')
	contents = config_file.read()
	contents = contents.split('\n')
	contents = [(x.split(':')[0], x.split(':')[1]) for x in contents]
	configs = {}
	for x in contents:
		configs[x[0]] = [e for e in x[1].split(' ') if e!='']
	return configs

def generate_audio():
	audio_name = inputfile+'_audio.mp4'
	cmd = 'ffmpeg -i '+inputfile+input_extension+' -c:a aac -b:a 128k -vn '+audio_name
	print(cmd)
	if not os.path.exists(audio_name):
		os.system(cmd)
	return audio_name

def generate_video(fps, bitrate, res):
	video_name_temp = inputfile+'_'+res+'_'+bitrate+'.mp4'
	cmd = 'ffmpeg -i '+inputfile+input_extension+' -s '+res+' -c:v libx264 -b:v '+bitrate+'k -g 90 -an '+video_name_temp
	print(cmd)
	video_name = inputfile+'_'+res+'_'+bitrate+'_'+fps+'.mp4'
	if not os.path.exists(video_name):
		if not os.path.exists(video_name_temp):
			os.system(cmd)
		os.system("ffmpeg -i "+video_name_temp+" -filter:v fps=fps="+fps+" "+video_name)
	return video_name

def generate_manifest(video_name, audio_name):
	cmd = 'mp4box -dash 5000 -rap -profile dashavc264:onDemand -mpd-title BBB -out manifest.mpd -frag 2000 '+audio_name+' '+video_name
	print(cmd)
	os.system(cmd)

def measure_cores(video_runtime, cores):
	global running
	if os.path.exists('cpu_freq.txt'):
		os.remove('cpu_freq.txt')
	playtime = 0
	while running:
		start = timeit.default_timer()
		os.system("adb shell echo $EPOCHREALTIME >> cpu_freq.txt")
		for c in range(cores):
			os.system("adb shell cat /sys/devices/system/cpu/cpu"+str(c)+"/online >> cpu_freq.txt")
		time.sleep(1)
		end = timeit.default_timer()
		playtime += (end - start)

def parse(video_name, cores):
	file = open("cpu_freq.txt","r")
	content = file.read().split("\n")
	content = np.array([content[i] for i in range(len(content)) if i%2 ==0])
	content = content[:-1].reshape((int(len(content)/(cores+1)),(cores+1)))
	prev = []
	for i in range(len(content)):
		if (i != len(content)-1):
			prev.append([float(content[i+1][0]) - float(content[i][0])])
		else:
			prev.append([0.0])
	content = np.concatenate((content, np.array(prev)), axis=1)
	content = [[float(a[0])]+[int(a[x]) for x in range(1,(cores+1))]+[float(a[cores+1])] for a in content]
	content = [a+[np.sum(a[1:cores+1])] for a in content]
	with open(video_name.split('.')[0]+'.csv', mode='w') as ds:
		dswriter = csv.writer(ds, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
		dswriter.writerow(['timestamp (s)']+['core '+str(i+1) for i in range(cores)]+['time difference from next measurement (s)', 'number of active cores'])
		for each in content:
			dswriter.writerow(each)


def runExp(configs, video_runtime):
	global filename, running, prevFrame, wait
	dfs = []
	fps = [default_fps] if 'fps' not in configs else configs['fps']
	bitrate = [default_bitrate] if 'bitrate' not in configs else configs['bitrate']
	res = [default_res] if 'res' not in configs else configs['res']
	cores = 4 if 'cores' not in configs else configs['cores'][0]
	audio_name = generate_audio()
	for f in fps:
		for b in bitrate:
			for r in res:
				video_name = generate_video(f,b,r)
				generate_manifest(video_name, audio_name)
				input("Play video and press enter to continue:")
				running, wait, prevFrame, filename = True, 0, 0, video_name.split(".")[0]
				measure_cores(video_runtime, int(cores))
				parse(video_name, int(cores))


import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import json

class S(BaseHTTPRequestHandler):
	def _set_headers(self):
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()

	def _html(self, message):
		"""This just generates an HTML document that includes `message`
		in the body. Override, or re-write this do do more interesting stuff.
		"""
		content = f"<html><body><h1>{message}</h1></body></html>"
		return content.encode("utf8")  # NOTE: must return a bytes object!

	def do_GET(self):
		self._set_headers()
		self.wfile.write(self._html("hi!"))

	def do_HEAD(self):
		self._set_headers()

	def do_POST(self):
		# Doesn't do anything with posted data
		global prevFrame,running,renderedFPS,filename,wait
		content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
		post_data = self.rfile.read(content_length).decode('utf8').replace("'", '"') # <--- Gets the data itself
		post_data = json.loads(post_data)
		if (int(post_data['totalFrames']) != prevFrame or int(post_data['totalFrames']) == 4) and running:
			print("first",post_data)
			renderedFPS += [post_data['frameRate']]
			prevFrame = int(post_data['totalFrames'])
			wait = 0
		elif prevFrame != 0 and wait == 5:
			print("second",post_data)
			running = False
			file = open("fps"+filename+".txt","w")
			file.write(str(renderedFPS))
			file.write("\n")
			file.write(post_data['totalFrames'])
			file.write("\n")
			file.write(post_data['droppedFrames'])
			file.close()
			renderedFPS = []
			prevFrame = 0
		else:
			print("third",post_data)
			prevFrame = int(post_data['totalFrames'])
			wait+=1
		self._set_headers()
		# self.wfile.write("<html><body><h1>POST!</h1></body></html>")


def run(server_class=HTTPServer, handler_class=S, addr="localhost", port=8333):
	server_address = (addr, port)
	httpd = server_class(server_address, handler_class)

	print(f"Starting httpd server on {addr}:{port}")
	httpd.serve_forever()


if __name__ == "__main__":

	parser = argparse.ArgumentParser(description="Run a simple HTTP server")
	parser.add_argument(
		"-l",
		"--listen",
		default="192.168.15.3",
		help="Specify the IP address on which the server listens",
	)
	parser.add_argument(
		"-p",
		"--port",
		type=int,
		default=8333,
		help="Specify the port on which the server listens",
	)
	args = parser.parse_args()
	print("listening started")
	configs = configuration()
	threading.Thread(target=runExp, args=(configs, 300)).start()
	run(addr=args.listen, port=args.port)
