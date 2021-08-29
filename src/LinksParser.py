import json
import re
import requests
import os
import urllib
import datetime
import math

# TODO move youtube_api_key to environmental variables
# TODO add message contents / more context to the jobject instances
# although this could be an issue because the final object is already like 40Mb
# with 10k processed links

def read_from_file(filepath):
	with open(filepath, 'r') as f:
		return f.read()

def write_to_file(filepath, contents):
	with open(filepath, "w") as f:
		f.write(contents)

def get_links_from_string(content):
	# https://www.geeksforgeeks.org/python-check-url-string/
	regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
	url = re.findall(regex,content)      
	links = [x[0] for x in url]
	if len(links) == 0:
		return []
	else:
		return links

def get_unique_links(jobject):
	links_dict = {}
	links = []
	messages = jobject["messages"]
	for message in messages:
		if "content" in message:
			message_links = get_links_from_string(message["content"])
			if len(message_links) != 0:
				for link in message_links:
					if link not in links_dict:
						links.append(link)
						links_dict[link] = True
	return list(reversed(links))

def timestamp_fits(timestamp, timestamp_limits):
	timestamp_min = None
	timestamp_max = None
	if timestamp_limits is not None:
		timestamp_min = timestamp_limits[0]
		timestamp_max = timestamp_limits[1]
	else:
		return True
	if (timestamp_min is not None and timestamp < timestamp_min) or (timestamp_max is not None and timestamp > timestamp_max):
		return False
	return True

def datetime_to_timestamp_ms(dt):
	return int(dt.timestamp() * 1e3)

# Returns a list of timestamp sorted objects from all supplied jobjects
# that represent facebook messenger json dump messages / conversation
# Is used in creation of the HTML page presenting the user with valid
# youtube videos, some of their data like title and address and such
# (obtained using youtube data API v3). Data like sender_name and
# itmestamp_ms is added for aditional info.
# Once a user ticks the videos from the HTML page the final download
# list is created. It can then be input into youtube-dl or some other
# downloader.
def get_unique_links_objects(jobjects, datetime_limits=None):
	timestamp_min = None
	timestamp_max = None
	if datetime_limits is not None:
		timestamp_min = datetime_to_timestamp_ms(datetime_limits[0])
		timestamp_max = datetime_to_timestamp_ms(datetime_limits[1])
	unique_dict = {}
	timestamp_dict = {}
	for jobject in jobjects:
		messages = jobject["messages"]
		for message in messages:
			timestamp = message["timestamp_ms"]
			if not timestamp_fits(timestamp, (timestamp_min, timestamp_max)):
				continue
			if "content" in message:
				message_links = get_links_from_string(message["content"])
				if len(message_links) != 0:
					for link in message_links:
						if link not in unique_dict:
							unique_dict[link] = True
							obj = {
								"sender_name": message["sender_name"],
								"link": link,
								"timestamp_ms": timestamp,
								"participants": jobject["participants"]
							}
							if message["timestamp_ms"] not in timestamp_dict:
								timestamp_dict[message["timestamp_ms"]] = [obj]
							else:
								timestamp_dict[message["timestamp_ms"]].append(obj)
	timestamp_dict_keys = sorted(timestamp_dict.keys(), reverse=False)
	final_objects = []
	for key in timestamp_dict_keys:
		final_objects += timestamp_dict[key]
	return final_objects

def get_youtube_links(links_objects):
	youtube_links = []
	for obj in links_objects:
		link = obj["link"]
		if is_youtube_link(link):
			youtube_links.append(obj)
	return youtube_links

def get_youtube_video_snippet(video_id, youtube_api_key):
	link = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={youtube_api_key}"
	try:
		res = requests.get(link)
		if res.status_code == 200:
			res_json = res.json()
			return res_json
		else:
			return None
	except Exception as e:
		return None

def is_youtube_link(urltxt):
	regex = f"^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$"
	url = re.findall(regex, urltxt)      
	links = [x[0] for x in url]
	if len(links) == 0:
		return []
	else:
		return links
		
def get_video_id(youtubeurl):
	regex = f"([\w\-]+)"
	matches = re.findall(regex,youtubeurl)
	video_id = None
	for match in matches:
		if len(match) == 11: # youtube video_ids are currently 11 characters long
			# overwrite previous match if found
			# sometimes parts of the url can appear to have the same length as video_id
			# example: https://www.youtube.com/CHANNELNAME?v=VIDEO_ID_XY
			# Try with get_video_id("https://www.youtube.com/CHANNELNAME?v=VIDEO_ID_XY")
			video_id = match
	return video_id

def get_playlist_id(youtubeurl):
	parts = youtubeurl.split("&")
	for part in parts:
		id_at = part.find("list=")
		if id_at != -1:
			return part[id_at+len("list="):]
	return None

def get_clean_youtube_link(video_id, playlist_id):
	if video_id == None:
		if playlist_id == None:
			# raise ValueError("Video ID cannot and Playlist ID cannot be none at the same time - check link formats and get_video_id().")
			return None
		return f"https://www.youtube.com/playlist?list={playlist_id}"
	clean_link = f"https://www.youtube.com/watch?v={video_id}"
	if playlist_id:
		clean_link += f"&list={playlist_id}"
	return clean_link

def add_clean_youtube_links(objects_youtube):
	for obj in objects_youtube:
		video_id = get_video_id(obj["link"])
		playlist_id = get_playlist_id(obj["link"])
		# #
		# Conditional breakpoint here (debug):
		# # video_id == None and playlist_id == None and "channel" not in obj["link"] and "/user/" not in obj["link"]
		obj["video_id"] = video_id
		obj["playlist_id"] = playlist_id
		link_clean = get_clean_youtube_link(video_id, playlist_id)
		if link_clean == None:
			# Is probably a channel or user link or something
			obj["link_clean"] = None #obj["link"]
			obj["selected"] = False
		else:
			obj["link_clean"] = link_clean
			obj["selected"] = True

def add_youtube_api_data(objects_youtube, youtube_api_key):
	counter = 1
	objects_youtube_len = len(objects_youtube)
	successful_requests = 0
	unsuccessful_requests = 0
	for obj in objects_youtube:
		print(f"Processing request {counter} / {objects_youtube_len}")
		# Only call the api if the youtube data hasn't been added yet
		if ("video_id" in obj and "youtube_data" not in obj) or ("youtube_data" in obj and "error" in obj["youtube_data"]): # "youtube_data" not in obj:
			snippet = get_youtube_video_snippet(obj["video_id"], youtube_api_key)
			if snippet != None:
				successful_requests += 1
				obj["youtube_data"] = snippet
			else:
				unsuccessful_requests	+= 1
				print(f"Error at request {counter}")
		counter += 1
	print(f"New successful requests: {successful_requests}")
	print(f"New unsuccessful requests: {unsuccessful_requests}")
	return unsuccessful_requests

# Returns True if the file doesn't already exist.
def download_file(url, filepath):
	path, filename = os.path.split(filepath) 
	if not os.path.isdir(path):
		os.makedirs(path)
	if not os.path.exists(filepath):
		try:
			res = urllib.request.urlretrieve(url, filepath)
		except Exception as e:
			print(f"Error while downloading file {url}")
		return True
	else:
		return False

def get_thumbnails(objects_youtube, output_folder):
	counter = 1
	objects_youtube_len = len(objects_youtube)
	successful_requests = 0
	unsuccessful_requests = 0
	for obj in objects_youtube:
		if "youtube_data" in obj and "error" not in obj["youtube_data"] and len(obj["youtube_data"]["items"]) != 0:
			print(f"Processing thumbnail {counter} / {objects_youtube_len}")
			# Get just the first video thumbnail in the list
			item = obj["youtube_data"]["items"][0]
			medium_url = item["snippet"]["thumbnails"]["medium"]["url"]
			url_path = urllib.parse.urlparse(medium_url).path
			file_extension = os.path.splitext(url_path)[1]
			output_filepath = os.path.join(output_folder, item["id"] + file_extension)
			is_new = download_file(medium_url, output_filepath)
			if is_new:
				if os.path.exists(output_filepath):
					successful_requests += 1
				else:
					unsuccessful_requests += 1
			obj["img_path"] = output_filepath
		counter += 1
	print(f"New successful requests: {successful_requests}")
	print(f"New unsuccessful requests: {unsuccessful_requests}")
	return unsuccessful_requests

def get_thumbnails_from_json(json_filename, output_folder):
	fstr = read_from_file(json_filename)
	jobj = json.loads(fstr)
	get_thumbnails(jobj, output_folder)
	write_to_file("processed_youtubedata_thumbnails.json", json.dumps(jobj, indent=2))

# get_thumbnails_from_json("processed_youtubedata.json", "res/web/thumbnails")
# print("DONE WITH THUMBNAILS")
# exit()

# Returns all filespaths that are used for storing messages
def get_matching_filepaths(root_folder):
	filepaths = []
	walkval = os.walk(root_folder, topdown=False, followlinks=False)
	for root, dirs, files in walkval:
		for file in files:
			if ".json" in file and "message" in file:
				filepaths.append(os.path.join(root, file))
	return filepaths

def reencode_string(str):
	return str.encode('latin1').decode('utf8')

# TODO create a general reencoder to fix any given json shape
def fix_jobject_encoding(jobject):
	for message in jobject["messages"]:
		if "content" in message:
			message["sender_name"] = reencode_string(message["sender_name"])
	for i in range(0, len(jobject["participants"])):
		jobject["participants"][i]["name"] = reencode_string(jobject["participants"][i]["name"])

# Transforms read message_X.json files to jobjects 
def get_jobjects(filepaths, fix_bad_facebook_encoding=False):
	jobjects = []
	for filepath in filepaths:
		jobject = json.loads(read_from_file(filepath))
		if fix_bad_facebook_encoding:
			fix_jobject_encoding(jobject)
		jobjects.append(jobject)
	return jobjects

# Used this to merge the objects because I forgot to include participants
# and have already made 10k queries with the prepared object without them
def merge_jobjects(main, added):
	for obj_main, obj_added in zip(main, added):
		if obj_main["link"] == obj_added["link"]:
			obj_main["participants"] = obj_added["participants"]
		else: # This is not supposed to happen when processing the same data but is added as a precaution
			print("WOOPS")
			print(obj_main["link"])
			print(obj_added["link"])
			print()
# main = json.loads(read_from_file("processed_youtubedata_thumbnails.json"))
# added = json.loads(read_from_file("processed_added.json"))
# merge_jobjects(main, added)
# write_to_file("processed_youtubedata_thumbnails_participants.json", json.dumps(main, indent=2))
# exit()

# Set selected of all elements to true/false
def set_selected_to(selected, jobject):
	for obj in jobject:
		obj["selected"] = selected
# main = json.loads(read_from_file("processed_youtubedata_thumbnails_participants.json"))
# set_selected_to(False, main)
# write_to_file("processed_youtubedata_thumbnails_participants.json", json.dumps(main, indent=2))
# exit()

# Main serves as a pipeline
# If a phase in the pipeline is skipped, the links_objects_youtube
# object tries to be obtained from the most advanced pipeline stage
# Read comments before each stage for more info
#
if __name__ == "__main__":
	youtube_api_key = None
	try:
		youtube_api_key = read_from_file("youtube_api_key")
	except Exception as e:
		print("Enter your YouTube Data API (v3) key into a file named 'youtube_api_key' in the project root.")
		exit(1)

	processed_dir = "processed"
	if not os.path.isdir(processed_dir):
		os.makedirs(processed_dir)
	
	# Third stage can only be turned on when all of the
	# links have been processed with Youtube Data API in stage 2
	#
	# You can manually switch them if you know what you're doing
	#
	# Generally speaking you can set the first stage to False
	# once you've generated a processed.json that you're happy with
	stages = [True, True, False]
	if stages == [False, False, False]:
		print("You should enable at least one of the stages 😒")
		exit(7)

	# You can adjust the datetime range limit to your liking
	# If you set the datetime_min to None then there will be no lower bound
	# If you set the datetime_max to None then there will be no upper bound
	# If you do not wish to limit the timestamp to anything, set datetime_limit to None
	datetime_min = datetime.datetime(2021, 3, 18)
	datetime_max = datetime.datetime(2021, 3, 20)
	datetime_limits = (datetime_min, datetime_max)
	datetime_limits = None

	links_objects_youtube = None

	# PART 1 - Generates base jobjects from Facebook json archives
	#
	if stages[0]:
		print("STAGE 1 📄: Generating base object from Facebook json archives")
		root_folder = None
		try:
			root_folder = read_from_file("root_folder")
		except Exception as e:
			print(r"Enter the path to your Facebook data archives into a file named 'root_folder' in the project root. Recommended: ...\messages\inbox")
			exit(2)
		filepaths = get_matching_filepaths(root_folder)
		jobjects = get_jobjects(filepaths, fix_bad_facebook_encoding=True)
		links_objects = get_unique_links_objects(jobjects, datetime_limits=datetime_limits)
		links_objects_youtube = get_youtube_links(links_objects)
		add_clean_youtube_links(links_objects_youtube)
		# Setting selected links to False turned out to be the best practice
		# when testing the LinkPicker.html for a long time
		set_selected_to(False, links_objects_youtube)
		write_to_file(os.path.join(processed_dir, "processed.json"), json.dumps(links_objects_youtube, indent=2))
		num_links = len(links_objects_youtube)
		print(f"Generated object contains {num_links} YouTube links.")
		if num_links > 10000:
			print(f"If you are using the default YouTube API key, you may need to run the second stage of the pipeline {math.ceil(num_links / 10000)} times.")
			print("(default rate limit is 10.000 requests per day)")
		print()

	# PART 2 - Add info from YouTube Data API (v3)
	#
	# Default YouTube Data API (v3) rate limits you to 10k requests per day
	# in case you have generated more than 10k objects in the first phase
	# of the pipeline you may need to rerun this part of the pipeline multiple times
	# The function add_youtube_api_data() knows where to pick off and should
	# continue if you supply with previously saved "processed_youtubedata.json"
	# 
	if stages[1]:
		print("STAGE 2 🔗: Adding info from YouTube Data API (v3)")
		if links_objects_youtube is None:
			try:
				links_objects_youtube = json.loads(read_from_file(os.path.join(processed_dir, "processed_youtubedata.json")))
				print(f"Loaded object contains {len(links_objects_youtube)} YouTube links.")
			except Exception as e:
				print("'processed_youtubedata.json' not found - trying to load from first stage.")
				# exit(3)
			if links_objects_youtube is None:
				try:
					links_objects_youtube = json.loads(read_from_file(os.path.join(processed_dir, "processed.json")))
					print(f"Loaded object contains {len(links_objects_youtube)} YouTube links.")
				except Exception as e:
					print("'processed.json' not found - start with the first step of the pipeline first.")
					exit(4)
		# Limit the number of links in case you feel like testing the API first
		# links_objects_youtube = links_objects_youtube[:5]
		unsuccessful_requests_num = add_youtube_api_data(links_objects_youtube, youtube_api_key)
		write_to_file(os.path.join(processed_dir, "processed_youtubedata.json"), json.dumps(links_objects_youtube, indent=2))
		print("Done with fetching youtube data for this pass.")
		# DONE? TODO how to actually determine whether or not it's ok to switch on the final stage - just turn it on for now
		if unsuccessful_requests_num == 0:
			stages[2] = True
		else:
			print("Check whether or not you need to repeat this step if you got rate limited.")
		print()

	# PART 3 - Downloads the video thumbnails and stores them in a resource folder
	#
	if stages[2]:
		print("STAGE 3 🖼️: Downloading video thumbnails")
		if links_objects_youtube is None:
			try:
				links_objects_youtube = json.loads(read_from_file(os.path.join(processed_dir, "processed_youtubedata_thumbnails.json")))
				print(f"Loaded object contains {len(links_objects_youtube)} YouTube links.")
			except Exception as e:
				print("'processed_youtubedata_thumbnails.json' not found - trying to load from second stage.")
				# exit(5)
			if links_objects_youtube is None:
				try:
					links_objects_youtube = json.loads(read_from_file(os.path.join(processed_dir, "processed_youtubedata.json")))
					print(f"Loaded object contains {len(links_objects_youtube)} YouTube links.")
				except Exception as e:
					print("'processed_youtubedata.json' not found - finishe the previous stage of the pipeline first.")
					exit(6)
		unsuccessful_requests_num = get_thumbnails(links_objects_youtube, "res/web/thumbnails")
		write_to_file(os.path.join(processed_dir, "processed_youtubedata_thumbnails.json"), json.dumps(links_objects_youtube, indent=2))
		if unsuccessful_requests_num == 0:
			print("Done with thumbnails")
		else:
			print(f"There were {unsuccessful_requests_num} unsuccessful requests - you might want to look into it if you want all of the thumbnails.")
		print()
		# DONE ? TODO when are you actually done? Check for conditions - in case you get rate limited
		# when downloading thumbnails

	print("✨ ALL DONE! ✨")
	print()
	print("Are you DONE done or do you need to repeat a step?")
	print("Getting no new unsuccessful requests at YouTube API and thumbnail fetching stages usually means you're good to go.")
	print()
	print("If you are DONE done, you can now open 'LinkPicker.html' and load the most recently generated '.json' file that is located in the 'processed' directory (best pick: 'processed_youtubedata_thumbnails.json').")
	print("Have fun exploring all of the old YouTube links you've sent between friends.")
	print("In case you want to archive certain videos close to your ❤, you can check out my Lyre project which is basically a youtube-dl frontent.")
	print()
	print("Signing off 🤖")
	print()
