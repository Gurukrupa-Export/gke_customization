# Copyright (c) 2026, Gurukrupa Export and contributors
# For license information, please see license.txt


# class GoldRates(Document):
	# pass

import frappe
import requests
from datetime import datetime
import pytz
from frappe.model.document import Document

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
        # doc.set_gold_value_6()

        
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
		# self.set_gold_value_6()


		
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




	# def set_gold_value_6(self):
	# 		if not (self.table_djrm and len(self.table_djrm) > 4):
	# 			return

	# 		rates = get_live_gold_rate()
	# 		ask  = rates.get("ask")
	# 		# high = rates.get("high")
	# 		# low  = rates.get("low")

	# 		if not ask:
	# 			frappe.msgprint("⚠️ Could not fetch live gold rate", indicator="orange")
	# 			return
	# 		import pytz
	# 		from datetime import datetime
	# 		# frappe.throw(str(ask))
	# 		ist = pytz.timezone('Asia/Kolkata')
	# 		self.table_djrm[4].set("live_rate", ask)
	# 		current_hour = datetime.now(pytz.utc).astimezone(ist).hour

	# 		if current_hour == 9:
	# 			field_name = "9_am"
	# 		elif current_hour == 15:
	# 			field_name = "3_pm"
	# 		elif current_hour == 23:
	# 			field_name = "11_pm"
	# 		else:
	# 			field_name = None

	# 		if field_name:
	# 			self.table_djrm[4].set(field_name, ask)





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
		# frappe.throw(str(gold_value))
		# if gold_value and self.table_djrm:
		if gold_value is not None and self.table_djrm:
			self.table_djrm[0].set("live_rate", gold_value)
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

			# if name == "GOLD 999 WITH GST IMP-IND":
			if name == "GOLD 999 WITH GST":
				ask = parts[-3]   

				if ask != "-":
					gold_value = float(ask)
				break
		# frappe.throw(str(gold_value))
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

# import frappe
# import websocket
# import json
# import gzip
# import base64
# import time
# from datetime import datetime
# import pytz


# # =========================================================
# # CONFIG
# # =========================================================

# HOST = "ws://ambicaaspot.com:1001/bullion?user=ambicaa&auth=1&type=web"

# RS = "\x1e"

# PRODUCT_NAME = "999-iMP-GOLD-1KG-today"


# # =========================================================
# # SIGNALR SEND
# # =========================================================

# def sr_send(ws, obj):

# 	payload = json.dumps(
# 		obj,
# 		separators=(",", ":")
# 	) + RS

# 	ws.send(payload)


# # =========================================================
# # DECODE GZIP DATA
# # =========================================================

# def decode_data(b64):

# 	compressed = base64.b64decode(b64)

# 	decompressed = gzip.decompress(compressed)

# 	text = decompressed.decode()

# 	return json.loads(text)


# # =========================================================
# # GET LIVE GOLD RATE
# # =========================================================

# def get_live_gold_rate():

# 	result = {
# 		"ask": None
# 	}

# 	def on_message(ws, message):

# 		parts = message.split(RS)

# 		for part in parts:

# 			part = part.strip()

# 			if not part:
# 				continue

# 			try:

# 				msg = json.loads(part)

# 			except Exception:
# 				continue

# 			# -------------------------------------------------
# 			# SIGNALR PING
# 			# -------------------------------------------------

# 			if msg.get("type") == 6:

# 				sr_send(ws, {"type": 6})

# 				continue

# 			# -------------------------------------------------
# 			# LIVE MARKET DATA
# 			# -------------------------------------------------

# 			if msg.get("target") == "workerPublish":

# 				try:

# 					data = decode_data(
# 						msg["arguments"][0]
# 					)

# 					products = data.get("products", [])

# 					gold_rate = next(
# 						(
# 							p for p in products
# 							if p.get("name") == PRODUCT_NAME
# 						),
# 						None
# 					)

# 					if gold_rate:

# 						result["ask"] = gold_rate.get("ask")

# 						ws.close()

# 				except Exception:

# 					frappe.log_error(
# 						frappe.get_traceback(),
# 						"Gold Rate Decode Error"
# 					)

# 	def on_open(ws):

# 		# -------------------------------------------------
# 		# SIGNALR HANDSHAKE
# 		# -------------------------------------------------

# 		sr_send(ws, {
# 			"protocol": "json",
# 			"version": 1
# 		})

# 		time.sleep(1)

# 		# -------------------------------------------------
# 		# SUBSCRIBE
# 		# -------------------------------------------------

# 		sr_send(ws, {
# 			"arguments": ["ambicaa"],
# 			"invocationId": "0",
# 			"target": "client",
# 			"type": 1
# 		})

# 	def on_error(ws, error):

# 		frappe.log_error(
# 			str(error),
# 			"Gold Rate Websocket Error"
# 		)

# 	ws = websocket.WebSocketApp(
# 		HOST,
# 		header=[
# 			"Origin: http://ambicaaspot.com",
# 			"User-Agent: Mozilla/5.0"
# 		],
# 		on_open=on_open,
# 		on_message=on_message,
# 		on_error=on_error
# 	)

# 	ws.run_forever(
# 		ping_interval=20,
# 		ping_timeout=10
# 	)

# 	return result


	
