import os

import yt_dlp
from flask import typing as ft, request, render_template, jsonify, Response
from flask.views import View

from Utils import ConfigIO

started_progress = {}

class UpdateDir(View):
	"""
	Using a POST method to retrieve the javascript id, value pair for one of the
	archive path(video, audio, book...)
	Response is the validated retrieved path. If this path is not a valid directory,
	send the previous path as response.
	"""
	methods = ['POST']

	def dispatch_request(self) -> ft.ResponseReturnValue:
		new_path = request.form.get("dir")
		dir_type = request.form.get("id")
		old_path = ConfigIO.get(dir_type)
		response = old_path
		if os.path.isdir(new_path):
			response = new_path
			ConfigIO.set(dir_type, new_path)
			print("Updating directory: %s = %s" % (dir_type, new_path))
		return Response(response=response, status=200)


class YoutubeDownloader(View):
	outputTypes = {'video': 'mp4/bestvideo/best', 'audio': 'm4a/bestaudio/best'}

	def dispatch_request(self) -> ft.ResponseReturnValue:
		return render_template("ydl.html", video_dir=ConfigIO.get("video_dir"), audio_dir=ConfigIO.get("audio_dir"))


class Downloader:
	def __init__(self, uuid, url, format):
		self.uuid = uuid
		self.url = url
		self.format = format
		self.cur = 0
		self.error = None
		self.title = ""

	def setTitle(self):
		with yt_dlp.YoutubeDL({}) as ydl:
			info_dict = ydl.extract_info(self.url, download=False)
			self.title = info_dict.get('title', '')
			ydl.close()

	def my_hook(self, d):
		try:
			self.cur = str(d["_percent_str"]).strip().replace("%", "")
			print("\nCurrent progress %s percent." % self.cur)
		except:
			print("\nUnknown progress percentage...")
		if d['status'] == 'finished':
			self.cur = 100

	def download_video(self):
		if self.format == "true":
			ext = 'mp4/bestvideo/best'
			output_dir = ConfigIO.get("video_dir"),
		else:
			ext = 'm4a/bestaudio/best'
			output_dir = ConfigIO.get("audio_dir"),
		print("requested format %s; output directory %s." % (ext, output_dir))
		ydl_opts = {
			"outtmpl": output_dir + '/%(title)s.%(ext)s',
			# this is where you can edit how you'd like the filenames to be formatted
			'progress_hooks': [self.my_hook],
			'format': ext,
		}
		with yt_dlp.YoutubeDL(ydl_opts) as ydl:
			self.error = ydl.download(self.url)
			ydl.close()


class ProgressData(View):
	def dispatch_request(self, uuid) -> ft.ResponseReturnValue:
		global started_progress
		if started_progress.get(uuid):
			downloader = started_progress[uuid]
		else:
			print("create new downloader " + uuid)
			downloader = Downloader(uuid, request.args.get("url"), request.args.get("format"))
			started_progress[uuid] = downloader
			try:
				downloader.setTitle()
				downloader.download_video()
			except Exception as ex:
				downloader.error = ex.__str__()
		if downloader.error or downloader.cur == 100:
			started_progress.pop(uuid, None)
		data = jsonify(label=downloader.title, cur=downloader.cur, error=downloader.error)
		print(data.get_json())
		return data
