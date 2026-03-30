# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt


# class GoldRates(Document):
	# pass

import frappe
import requests
from datetime import datetime
import pytz
from frappe.model.document import Document
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from bs4 import BeautifulSoup
# from frappe.utils import now_datetime

def run_gold_rate_scheduler():
    try:
        today = frappe.utils.today()

        name = frappe.db.exists("Gold Rates", {"date": today})

        if name:
            doc = frappe.get_doc("Gold Rates", name)
            # action = "Updated"
        else:
            doc = frappe.new_doc("Gold Rates")
            doc.date = today
            doc.add_default_rows()
            # action = "Created"

        doc.set_gold_value()
        doc.get_gold_value_1()
        doc.set_gold_rate_2()
        doc.get_gold_rate_3()
        doc.get_gold_rate_4()
        doc.set_gold_rate_5()
        doc.set_gold_value_6()

        
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        # print(f"✅ {action}: {doc.name}")

        frappe.logger().info(f"Gold Rate Scheduler {action}: {doc.name}")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Gold Rate Scheduler Error")



class GoldRates(Document):
	def validate(self):
		self.set_gold_value()
		self.get_gold_value_1()
		self.set_gold_rate_2()
		self.get_gold_rate_3()
		self.get_gold_rate_4()
		self.set_gold_rate_5()
		self.set_gold_value_6()



		
	def add_default_rows(self):
		if not self.table_djrm or len(self.table_djrm) == 0:
			default_rows = [
				{"particulars": "Jain Jewels", "city": "Surat"},
				{"particulars": "J K Sons", "city": "Ahmedabad"},
				{"particulars": "Arihant", "city": "Mumbai"},
				{"particulars": "Mohanlal", "city": "Chennai"},
				{"particulars": "Ambica", "city": "Bangalore"},
				{"particulars": "Shiv Sahai", "city": "Chennai"},
				{"particulars": "SLN Bullion", "city": "Vijaywada"}
			]

			for row in default_rows:
				self.append("table_djrm", row)




	def set_gold_value_6(self):
			if not (self.table_djrm and len(self.table_djrm) > 4):
				return

			rates = get_live_gold_rate()
			ask  = rates.get("ask")
			high = rates.get("high")
			low  = rates.get("low")

			if not ask:
				frappe.msgprint("⚠️ Could not fetch live gold rate", indicator="orange")
				return
			import pytz
			from datetime import datetime

			ist = pytz.timezone('Asia/Kolkata')
			self.table_djrm[4].set("live_rate", high)
			current_hour = datetime.now(pytz.utc).astimezone(ist).hour

			if current_hour == 9:
				field_name = "9_am"
			elif current_hour == 15:
				field_name = "3_pm"
			elif current_hour == 23:
				field_name = "11_pm"
			else:
				field_name = None

			if field_name:
				self.table_djrm[4].set(field_name, high)





	def set_gold_value(self):
		URL = "http://bcast.jainbullion.in:7767/VOTSBroadcastStreaming/Services/xml/GetLiveRateByTemplateID/jain"

		try:
			response = requests.get(URL, timeout=10)
			response.raise_for_status()
			response_text = response.text
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Gold Rate Fetch Error")
			return

		gold_value = None

		for line in response_text.strip().splitlines():
			parts = line.split()

			# GOLD 999 WITH TDS row (4972)
			if len(parts) >= 8 and parts[0] == "4972":
				try:
					gold_value = float(parts[7])
					break
				except ValueError:
					continue

		# if gold_value and self.table_djrm:
		if gold_value is not None and self.table_djrm:
			self.table_djrm[0].set("live_rate", gold_value)
			ist = pytz.timezone('Asia/Kolkata')
			current_hour = datetime.now(ist).hour
			if current_hour == 11:
				field_name = "9_am"
			elif current_hour == 15:  
				field_name = "3_pm"
			elif current_hour == 23:  
				field_name = "11_pm"
			else:
				field_name = None  

			if field_name and len(self.table_djrm) > 5:
				self.table_djrm[0].set(field_name, gold_value)




	def get_gold_value_1(self):
		URL = "https://bcast.jksons.in:7768/VOTSBroadcastStreaming/Services/xml/GetLiveRateByTemplateID/jksons"
		# resp = frappe.make_get_request(url=URL)
		response = requests.get(URL, timeout=10)
		response.raise_for_status()
		response_text = response.text

		gold_value = None

		for line in str(response_text).strip().splitlines():
			parts = line.split()

			if len(parts) < 5:
				continue

			name = " ".join(parts[1:-4]).strip().upper()

			if name == "GLD 999 IMP AMD T+1":
				rate = parts[-3]   

				if rate != "-":
					gold_value = float(rate)
				break

		# if gold_value and self.table_djrm:
		# 	self.table_djrm[1].set("9_am", gold_value)
		if gold_value is not None and self.table_djrm:
			self.table_djrm[1].set("live_rate", gold_value)
			ist = pytz.timezone('Asia/Kolkata')
			current_hour = datetime.now(ist).hour
			if current_hour == 9:
				field_name = "9_am"
			elif current_hour == 15: 
				field_name = "3_pm"
			elif current_hour == 23: 
				field_name = "11_pm"
			else:
				field_name = None  

			if field_name and len(self.table_djrm) > 5:
				self.table_djrm[1].set(field_name, gold_value)












	def set_gold_rate_2(self):
		URL = "https://bcast.arihantspot.com:7768/VOTSBroadcastStreaming/Services/xml/GetLiveRateByTemplateID/arihant"

		try:
			response = requests.get(URL, timeout=10)
			response.raise_for_status()
			response_text = response.text

		except Exception:
			frappe.log_error(frappe.get_traceback(), "Gold Rate Fetch Error")
			return

		gold_value = None

		for line in response_text.strip().splitlines():
			parts = line.split()

			if len(parts) < 5:
				continue

			name = " ".join(parts[1:-4]).strip().upper()

			if name == "GOLD 999 WITH GST IMP-IND":
				ask = parts[-3]   

				if ask != "-":
					gold_value = float(ask)
				break

		# if gold_value:
		# 	if len(self.table_djrm) > 2:
		# 		self.table_djrm[2].set("9_am", gold_value)
		if gold_value is not None and self.table_djrm:
			self.table_djrm[2].set("live_rate", gold_value)
			ist = pytz.timezone('Asia/Kolkata')
			current_hour = datetime.now(ist).hour
			if current_hour == 9:
				field_name = "9_am"
			elif current_hour == 15: 
				field_name = "3_pm"
			elif current_hour == 23:
				field_name = "11_pm"
			else:
				field_name = None  

			if field_name and len(self.table_djrm) > 5:
				self.table_djrm[2].set(field_name, gold_value)


	




	

	def get_gold_rate_3(self):
		URL = "https://bcprice.logimaxindia.com/lmxtrade/winbullliteapi/api/v1/broadcastrates"

		headers = {
			"Content-Type": "application/json"
		}

		payload = {
			"client": "mohanlal"
		}

		try:
			response = requests.post(URL, json=payload, headers=headers, timeout=10)
			response.raise_for_status()
			response_text = response.text

		except Exception:
			frappe.log_error(frappe.get_traceback(), "Gold Rate Fetch Error")
			return

		gold_rate = None

		for line in response_text.strip().splitlines():

			if "GOLD (PURE) INCL OF GST & TDS" in line:

				parts = line.split()

				try:
					gold_rate = float(parts[10])
				except (IndexError, ValueError):
					frappe.log_error("Gold rate parsing failed", "Gold Rate Parse Error")
					return

				break

		# if gold_rate:
		# 	gold_value = gold_rate * 10   
		# 	if len(self.table_djrm) > 2:
		# 		self.table_djrm[3].set("9_am", gold_value)
		if gold_rate is not None and self.table_djrm:
			gold_value = gold_rate * 10 
			self.table_djrm[3].set("live_rate", gold_value)
			ist = pytz.timezone('Asia/Kolkata')
			current_hour = datetime.now(ist).hour
			if current_hour == 9:
				field_name = "9_am"
			elif current_hour == 15:
				field_name = "3_pm"
			elif current_hour == 23:
				field_name = "11_pm"
			else:
				field_name = None 

			if field_name and len(self.table_djrm) > 5:
				self.table_djrm[3].set(field_name, gold_value)








	def get_gold_rate_4(self):
		URL = "http://13.200.166.91/lmxtrade/winbullliteapi/api/v1/broadcastrates"
		headers = {
        "Content-Type": "application/json"
			}

		payload = {
			"client": "ssahaitrd"
		}

		resp = requests.post(URL, json=payload, headers=headers, timeout=10)

		gold_rate = None

		for line in resp.text.strip().splitlines():

			if '"GLD CHN PURE"' in line:

				parts = line.split("\t")

				gold_rate = float(parts[4])
				break
		# if gold_rate:
		# 	gold_value = gold_rate * 10   
		# 	if len(self.table_djrm) > 2:
		# 		self.table_djrm[5].set("9_am", gold_value)
		

		if gold_rate is not None and self.table_djrm:
			gold_value = gold_rate * 10
			self.table_djrm[5].set("live_rate", gold_value) 
			ist = pytz.timezone('Asia/Kolkata')
			current_hour = datetime.now(ist).hour
			if current_hour == 9:
				field_name = "9_am"
			elif current_hour == 15: 
				field_name = "3_pm"
			elif current_hour == 23: 
				field_name = "11_pm"
			else:
				field_name = None 

			if field_name and len(self.table_djrm) > 5:
				self.table_djrm[5].set(field_name, gold_value)
		





	def set_gold_rate_5(self):
		URL = "https://bcast.slnbullion.com/VOTSBroadcastStreaming/Services/xml/GetLiveRateByTemplateID/sln"

		try:
			response = requests.get(URL, timeout=10)
			response.raise_for_status()
			response_text = response.text

		except Exception:
			frappe.log_error(frappe.get_traceback(), "Gold Rate Fetch Error")
			return

		gold_value = None

		gold_value = None
		target = "GOLD VJA IMP (999) T+1"

		for line in response_text.strip().splitlines():
			clean_line = " ".join(line.upper().split())

			if target in clean_line:
				parts = clean_line.split()

				# find "-" and take next numeric value
				for i, val in enumerate(parts):
					if val == "-" and i + 1 < len(parts):
						try:
							gold_value = float(parts[i + 1])  # ✅ 14319.30
							break
						except ValueError:
							continue
				break
		# frappe.throw(str(gold_value))
		if gold_value is not None and self.table_djrm:
			self.table_djrm[6].set("live_rate", gold_value*10)
			ist = pytz.timezone('Asia/Kolkata')
			current_hour = datetime.now(ist).hour
			if current_hour == 9:
				field_name = "9_am"
			elif current_hour == 15: 
				field_name = "3_pm"
			elif current_hour == 23: 
				field_name = "11_pm"
			else:
				field_name = None  

			if field_name and len(self.table_djrm) > 6:
				self.table_djrm[6].set(field_name, gold_value*10 )







# gold_rates_branch_wise.py

import frappe
import socket
import base64
import json
import time
import os
from frappe.model.document import Document


def ws_handshake(host, port, path):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.settimeout(15)
	sock.connect((host, port))
	key = base64.b64encode(os.urandom(16)).decode()
	handshake = (
		f"GET {path} HTTP/1.1\r\n"
		f"Host: {host}:{port}\r\n"
		f"Upgrade: websocket\r\n"
		f"Connection: Upgrade\r\n"
		f"Sec-WebSocket-Key: {key}\r\n"
		f"Sec-WebSocket-Version: 13\r\n"
		f"Origin: http://ambicaaspot.com\r\n"
		f"\r\n"
	)
	sock.send(handshake.encode())
	response = sock.recv(4096).decode('utf-8', errors='ignore')
	if "101 Switching Protocols" not in response:
		raise Exception(f"WebSocket upgrade failed: {response[:200]}")
	return sock


def ws_send(sock, message):
	msg = message.encode('utf-8')
	length = len(msg)
	mask = os.urandom(4)
	frame = bytearray()
	frame.append(0x81)
	if length <= 125:
		frame.append(0x80 | length)
	elif length <= 65535:
		frame.append(0x80 | 126)
		frame.append((length >> 8) & 0xFF)
		frame.append(length & 0xFF)
	else:
		frame.append(0x80 | 127)
		for i in range(7, -1, -1):
			frame.append((length >> (8 * i)) & 0xFF)
	frame.extend(mask)
	frame.extend(bytearray(b ^ mask[i % 4] for i, b in enumerate(msg)))
	sock.send(bytes(frame))


def ws_recv(sock):
	try:
		header = sock.recv(2)
		if len(header) < 2:
			return None
		opcode = header[0] & 0x0F
		if opcode == 0x8:
			return None
		payload_len = header[1] & 0x7F
		if payload_len == 126:
			payload_len = int.from_bytes(sock.recv(2), 'big')
		elif payload_len == 127:
			payload_len = int.from_bytes(sock.recv(8), 'big')
		payload = b''
		while len(payload) < payload_len:
			chunk = sock.recv(payload_len - len(payload))
			if not chunk:
				break
			payload += chunk
		return payload.decode('utf-8', errors='ignore')
	except socket.timeout:
		return ""


def get_live_gold_rate():
	host = "dashboard.ambicaaspot.com"
	port = 10001
	product_name = "IND-GOLD[999]-1KG --today"
	result = {"ask": None, "bid": None, "high": None, "low": None}
	sock = None

	try:
		# Step 1: HTTP poll to get SID
		import urllib.request
		url = f"http://{host}:{port}/socket.io/?EIO=4&transport=polling"
		req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
		with urllib.request.urlopen(req, timeout=10) as r:
			raw = r.read().decode()
		sid = json.loads(raw[raw.index('{'):])["sid"]

		# Step 2: Upgrade to WebSocket
		sock = ws_handshake(host, port, f"/socket.io/?EIO=4&transport=websocket&sid={sid}")

		# Step 3: Probe + upgrade
		ws_send(sock, "2probe")
		time.sleep(0.2)
		ws_recv(sock)       # expect "3probe"
		ws_send(sock, "5")  # upgrade confirm

		# Step 4: Auth
		ws_send(sock, '40' + json.dumps({"auth": {"type": "web", "token": "starline@123"}}))
		time.sleep(0.3)
		ws_recv(sock)       # expect 40{sid:...}

		# Step 5: Emit Client event
		ws_send(sock, '42' + json.dumps(["Client", "ambicaaspot"]))

		# Step 6: Read messages until we find gold rate
		sock.settimeout(3)
		for _ in range(20):
			msg = ws_recv(sock)
			if msg is None:
				break
			if msg == "" or msg == "2":
				ws_send(sock, "2")  # pong
				continue
			if product_name in msg:
				prod_idx = msg.index(product_name)
				obj_start = msg.rindex('{', 0, prod_idx)
				depth = 0
				obj_end = obj_start
				for k in range(obj_start, len(msg)):
					if msg[k] == '{':
						depth += 1
					elif msg[k] == '}':
						depth -= 1
						if depth == 0:
							obj_end = k + 1
							break
				rate_obj = json.loads(msg[obj_start:obj_end])
				result["ask"]  = rate_obj.get("Ask")
				result["bid"]  = rate_obj.get("Bid")
				result["high"] = rate_obj.get("High")
				result["low"]  = rate_obj.get("Low")
				return result

	except Exception as e:
		frappe.log_error(str(e), "Gold Rate Fetch Error")
	finally:
		if sock:
			try:
				sock.close()
			except Exception:
				pass

	return result

