# Copyright (c) 2023, gurukrupa_export] and contributors
# For license information, please see license.txt

import frappe
import pandas as pd
# import easyocr
import requests,json
# from bs4 import BeautifulSoup
from urllib.parse import urljoin
# from pdf2image import convert_from_path
import numpy as np
from frappe.model.document import Document
import torch
import datetime
from PyPDF2 import PdfReader
from fnmatch import fnmatch
import subprocess,os

# to clear Cuda Cache memory 
# torch.cuda.empty_cache()


class GJEPCMetalRate(Document):
	# def onload(self):
		# self.custom_rate_in_usd_
	pass


@frappe.whitelist()
def get_gjepc_rate():
	url = "https://prices.lbma.org.uk/json/gold_pm.json?r=503825991"

	payload = {}
	headers = {
	'authority': 'prices.lbma.org.uk',
	'accept': 'application/json',
	'accept-language': 'en-US,en;q=0.9',
	'origin': 'https://www.lbma.org.uk',
	'referer': 'https://www.lbma.org.uk/prices-and-data/precious-metal-prices',
	'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
	'sec-ch-ua-mobile': '?0',
	'sec-ch-ua-platform': '"Windows"',
	'sec-fetch-dest': 'empty',
	'sec-fetch-mode': 'cors',
	'sec-fetch-site': 'same-site',
	'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
	}

	response = requests.request("GET", url, headers=headers, data=payload)
	json_data = json.loads(response.text)
	gjepc_rate = json_data[-1]['v'][0]
	# print(json_data)
	usd_kt_22 = round(float((gjepc_rate)*22)/24,2)
	usd_kt_18 = round((float(gjepc_rate)*18)/24,2)
	usd_kt_14 = round((float(gjepc_rate)*14)/24,2)
	usd_kt_10 = round((float(gjepc_rate)*10)/24,2)
	return ['24KT',float(gjepc_rate)],['22KT',usd_kt_22],['18KT',usd_kt_18],['14KT',usd_kt_14],['10KT',usd_kt_10]


@frappe.whitelist()
def get_gjepc_file():
	
	url = "https://gjepc.org/gold-rates.php"

	payload = {}
	headers = {
	'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
	'Accept-Language': 'en-US,en;q=0.9',
	'Cache-Control': 'max-age=0',
	'Connection': 'keep-alive',
	'Cookie': '_fbp=fb.1.1687235791539.835432400; _gcl_au=1.1.484288729.1687235792; PHPSESSID=7jqfadcogspshs1v1ug8225hgr; _gid=GA1.2.570433648.1689654652; TS014fb849=012fed3edf035b1a205ea29995c461b51e73daf6eb4927b0266685ff2493776346dc72029ac01c09d0c39a1ad8a9c8ea2e13e4f880; _ga_04GCDQS8D6=GS1.1.1689665100.4.1.1689665101.0.0.0; _ga=GA1.1.1063203251.1687235791; TS09ed7361027=0897ff9122ab2000ba4d69ef1779aa4a0a81b73c3b6dc217efade3f1661279810be69b9121186cf208b28cc91b1130006a21b9f0e886c3e5c94bf9ad8be10aaafd0034101df333c8d0dc9f8b4ee0a06c98b479c94993e2d695e479a1617b9be0; TS014fb849=012fed3edfd0e89b50de33580d7bb39b2440669b1aaac79f98b9008e89aced0bafe051bd0d4c4cd8815110b47408b7dea38313c493; TS09ed7361027=0897ff9122ab20002b9c58e096a79c840f984996829643ca396fdf667528ecfc71aaa508bf846f8f088d5fc3c6113000d58f989c9708661f967f77c098e198fe56e13cd7c2efc321f17ce03617398e9b1e59f0d88e918aa58dfa555afc41e115',
	'Sec-Fetch-Dest': 'document',
	'Sec-Fetch-Mode': 'navigate',
	'Sec-Fetch-Site': 'none',
	'Sec-Fetch-User': '?1',
	'Upgrade-Insecure-Requests': '1',
	'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
	'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
	'sec-ch-ua-mobile': '?0',
	'sec-ch-ua-platform': '"Windows"'
	}

	response = requests.request("GET", url, headers=headers, data=payload)
	file_name = response.text.split('<a href="admin/GoldRate/')[1].split('"')[0]

	return file_name


@frappe.whitelist()
def get_today_date():
	# using now() to get current time
	current_time = datetime.datetime.now()
	return current_time