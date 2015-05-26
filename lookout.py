#!/usr/bin/env python

PORT = 9890

import flask, os, sys, time, psutil, json, socket
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from multiprocessing import Process, Manager
import platform, subprocess

if getattr(sys, 'frozen', None):
	static = os.path.join(sys._MEIPASS, 'static')
else:
	static = 'static'

app = flask.Flask(__name__, static_folder=static)

@app.route('/')
def frontend():
	return flask.send_from_directory(app.static_folder, 'index.html')

@app.route('/raw')
def raw():
	return flask.Response(
		json.dumps(stats.copy()),
		mimetype='application/json'
	)

def get_num_updates():
    avail = 0
    security = 0
    if platform.linux_distribution()[0] == 'Ubuntu':
        out = subprocess.check_output("/usr/lib/update-notifier/update-motd-updates-available", stderr=subprocess.STDOUT)
        out = out.strip().splitlines()
        if len(out) > 1:
            avail = int(out[0].split()[0])
            security = int(out[1].split()[0])
    return [avail, security]

def get_req_reboot():
    if platform.linux_distribution()[0] == 'Ubuntu':
        out = subprocess.check_output("/usr/lib/update-notifier/update-motd-reboot-required", stderr=subprocess.STDOUT)
        if out.strip() == "":
            return True
    return False

def update(stats):
	while True:
		diskused = 0
		disktotal = 0
		for i in psutil.disk_partitions():
			try:
				x = psutil.disk_usage(i.mountpoint)
				diskused += x.used
				disktotal += x.total
			except OSError:
				pass
		stats['uptime'] = time.time() - psutil.BOOT_TIME
		stats['fqdn'] = socket.getfqdn()
		stats['cpuusage'] = psutil.cpu_percent(0)
		stats['ramusage'] = psutil.virtual_memory()
		stats['diskio'] = psutil.disk_io_counters()
		stats['diskusage'] = [diskused, disktotal]
		stats['netio'] = psutil.net_io_counters()
		stats['swapusage'] = psutil.swap_memory()
		stats['updates'] = get_num_updates()
		stats['reboot'] = get_req_reboot()
		time.sleep(1)
		
if __name__ == '__main__':
	stats = Manager().dict()
	Process(target=update, args=(stats, )).start()
	if len(sys.argv) > 1:
		PORT = sys.argv[1]
	server = HTTPServer(WSGIContainer(app))
	print 'Now listening on port ' + str(PORT)
	server.listen(PORT)
	IOLoop.instance().start()
