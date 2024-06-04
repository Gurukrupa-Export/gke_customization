# Copyright (c) 2024, Gurukrupa Export and contributors
# For license information, please see license.txt

import frappe,requests
from frappe.model.document import Document
import itertools
from itertools import groupby
from frappe.utils import get_link_to_form

metal_touch_dict = {
	92:"22KT",
	76:"18KT",
	}

metal_colour_dict = {
	"YELLOW GOLD":"Yellow",
	"YELLOW + WHITE":"Yellow+White",
	"WHITE GOLD":"White",
	"PINK GOLD":"Pink",
	"PINK + WHITE":"Pink+White",
}

cut_or_cab_dict = {
	"Ruby":"Cut",
	"White Water Pearl":"Cab",
	"Coral":"Cab",
	"Emerald":"Cut",
	"Yellow Shappire":"Cut",
	"Blue Shappire":"Cut",
	"Cat'S Eye":"Cab",
	"Hessonite":"Cut",
	}

class OldBOM(Document):
	def before_insert(self):
		created = frappe.db.get_value("Old Stylebio Master",{"old_stylebio":self.old_stylebio},"created")
		if created == 1:
			frappe.throw("Already created")
	

	def after_insert(self):
		if not self.old_bom_metal_details:
			name = frappe.db.get_value("Old Stylebio Master",{"old_stylebio":self.old_stylebio},"name")

			all_tagno_against_stylebio = frappe.db.sql(f"""select tag_no from `tabOld Stylebio Master Table` where parent = '{name}'""",as_list=1)
			final_all_tagno_against_stylebio = []
			if all_tagno_against_stylebio:
				for a in all_tagno_against_stylebio:
					final_all_tagno_against_stylebio.append(a[0])

			session = requests.Session()
			response = session.get(f"http://3.6.177.5:5000/api/stylebio/{self.old_stylebio}")
			json_data = response.json()['data']
			old_bom_doc = frappe.get_doc("Old BOM",{"old_stylebio":self.old_stylebio})
			# old_bom_doc.old_stylebio = self.old_stylebio
			
			for m in json_data.keys():
				if m not in final_all_tagno_against_stylebio:
					continue
				if json_data[m]['metal_data']:
					metal_dict = old_bom_doc.append("old_bom_metal_details", {})
					metal_dict.tag_no = m
					metal_dict.old_stylebio = self.old_stylebio
					metal_dict.metal_type = 'Gold'
					metal_dict.metal_touch = metal_touch_dict[json_data[m]['metal_data']['Metal_Ratio']]
					metal_dict.metal_purity = str(float(json_data[m]['metal_data']['Metal_Ratio']))
					try:
						metal_dict.metal_colour = metal_colour_dict[json_data[m]['metal_data']['Metal_Color']]
					except:
						metal_dict.metal_colour = "see design tag/cad"
					metal_dict.metal_weight = json_data[m]['metal_data']['G_Weight']

				if json_data[m]['diamond_data']:
					diamond_dict = old_bom_doc.append("old_bom_diamond_details", {})
					diamond_dict.tag_no = m
					diamond_dict.old_stylebio = self.old_stylebio
					diamond_dict.diamond_type = "Real"
					diamond_dict.diamond_shape = str(json_data[m]['diamond_data']['Shape_Name']).capitalize()
					diamond_dict.diamond_sieve_size = json_data[m]['diamond_data']['Type']
					diamond_dict.diamond_pcs = json_data[m]['diamond_data']['Pcs']
					diamond_dict.diamond_weight = json_data[m]['diamond_data']['Dia_Wt']

				if json_data[m]['gemstone_data']:
					for gt in json_data[m]['gemstone_data']['ERP_Name'].split(','):
						gemstone_dict = old_bom_doc.append("old_bom_gemstone_details", {})
						gemstone_dict.tag_no = m
						gemstone_dict.old_stylebio = self.old_stylebio
						
						gemstone_dict.gemstone_type = gt.lstrip().title()
						if len(json_data[m]['gemstone_data']['ERP_Name'].split(',')) == 1:
							gemstone_dict.cut_or_cab = json_data[m]['gemstone_data']['Cut_or_Cab'].lower().replace("cut","Faceted").replace("cab","Cabochon")
						else:
							gemstone_dict.cut_or_cab = cut_or_cab_dict[gt.lstrip().title()].lower().replace("cut","Faceted").replace("cab","Cabochon")
						gemstone_dict.gemstone_shape = json_data[m]['gemstone_data']['Shape']

						gemstone_dict.gemstone_quality = json_data[m]['gemstone_data']['Quality'].replace("Semi Precious","Semi-Precious")
						gemstone_dict.gemstone_grade = json_data[m]['gemstone_data']['Grade']
						gemstone_dict.total_gemstone_rate = json_data[m]['gemstone_data']['Amount']

						gemstone_dict.gemstone_size = (json_data[m]['gemstone_data']['Size_Name'].replace(" X ","*") + " MM").replace("MM MM","MM")
						gemstone_dict.gemstone_pcs = json_data[m]['gemstone_data']['Pcs']
						gemstone_dict.gemstone_weight = json_data[m]['gemstone_data']['Weight']
						gemstone_dict.per_pcs_per_carat = json_data[m]['gemstone_data']['UOM'].replace('Per Piece','Per Pc').replace('Per Pcarat','Per Pc')
						if gemstone_dict.per_pcs_per_carat == '':
							gemstone_dict.per_pcs_per_carat = "see design tag/cad"

			old_bom_doc.save()
			frappe.db.set_value('Old Stylebio Master',{'old_stylebio':self.old_stylebio},'created',1)

			
	def on_submit(self):
		old_bom_metal_details = []
		for i in self.old_bom_metal_details:
			metal_data = {}
			metal_data['tag_no'] = i.tag_no
			metal_data['stylebio'] = i.old_stylebio
			metal_data['metal_touch'] = i.metal_touch
			metal_data['metal_purity'] = i.metal_purity
			metal_data['metal_color'] = i.metal_colour
			metal_data['metal_weight'] = i.metal_weight
			metal_data['metal_data'] = 1
			old_bom_metal_details.append(metal_data)

		for i in self.old_bom_diamond_details:
			diamond_data = {}
			diamond_data['tag_no'] = i.tag_no
			diamond_data['stylebio'] = i.old_stylebio
			diamond_data['diamond_shape'] = i.diamond_shape
			diamond_data['sieve_size'] = i.diamond_sieve_size
			diamond_data['diamond_pcs'] = i.diamond_pcs
			diamond_data['diamond_weight'] = i.diamond_weight
			diamond_data['diamond_data'] = 1
			old_bom_metal_details.append(diamond_data)

		for i in self.old_bom_gemstone_details:
			gemstone_data = {}
			gemstone_data['tag_no'] = i.tag_no
			gemstone_data['stylebio'] = i.old_stylebio
			gemstone_data['gemstone_type'] = i.gemstone_type
			gemstone_data['cut_or_cab'] = i.cut_or_cab
			gemstone_data['gemstone_shape'] = i.gemstone_shape
			gemstone_data['gemstone_quality'] = i.gemstone_quality
			gemstone_data['gemstone_grade'] = i.gemstone_grade
			gemstone_data['gemstone_size'] = i.gemstone_size
			gemstone_data['gemstone_pcs'] = i.gemstone_pcs
			gemstone_data['gemstone_weight'] = i.gemstone_weight
			gemstone_data['total_gemstone_rate'] = i.total_gemstone_rate
			gemstone_data['gemstone_data'] = 1
			gemstone_data['per_pcs_per_carat'] = i.per_pcs_per_carat
			old_bom_metal_details.append(gemstone_data)
		
		sorted_data = sorted(old_bom_metal_details, key=lambda x: x['tag_no'])
		grouped_data = {}
		for key, group in groupby(sorted_data, key=lambda x: x['tag_no']):
			subgrouped_data = {"tagno": key, "metal_data": [], "diamond_data": [], "gemstone_data":[]}
			for item in group:
				if "metal_data" in item:
					subgrouped_data["metal_data"].append(item)
				elif "diamond_data" in item:
					subgrouped_data["diamond_data"].append(item)
				else:
					subgrouped_data["gemstone_data"].append(item)
			grouped_data[key] = subgrouped_data

		for j in grouped_data.keys():
			item_code = frappe.db.get_value('Item',{'old_tag_no':j},'name')
			if item_code:
				# frappe.throw(item_code)
				bom_doc = frappe.new_doc("BOM")
				bom_doc.item = item_code
				bom_doc.is_default = 1
				bom_doc.is_active = 1
				bom_doc.bom_type = "Template"
				bom_doc.company = "Gurukrupa Export Private Limited"

				for m in grouped_data[j]['metal_data']:
					metal_detail = bom_doc.append("metal_detail", {})
					metal_detail.metal_type = "Gold"
					metal_detail.metal_touch = m['metal_touch']
					metal_detail.metal_purity = m['metal_purity']
					metal_detail.metal_colour = m['metal_color']
					metal_detail.quantity = m['metal_weight']
				
				for d in grouped_data[j]['diamond_data']:
					diamond_detail = bom_doc.append("diamond_detail", {})
					diamond_detail.diamond_type = "Real"
					diamond_detail.stone_shape = d['diamond_shape']
					diamond_detail.diamond_sieve_size = d['sieve_size']
					diamond_detail.pcs = d['diamond_pcs']
					diamond_detail.quantity = d['diamond_weight']
					diamond_detail.sub_setting_type = "Close Setting"

				for g in grouped_data[j]['gemstone_data']:
					gemstone_detail = bom_doc.append("gemstone_detail", {})
					gemstone_detail.gemstone_type = g['gemstone_type']
					gemstone_detail.cut_or_cab = g['cut_or_cab']
					gemstone_detail.stone_shape = g['gemstone_shape']
					gemstone_detail.gemstone_quality = g['gemstone_quality']
					gemstone_detail.gemstone_grade = g['gemstone_grade']
					gemstone_detail.gemstone_size = g['gemstone_size']
					gemstone_detail.pcs = g['gemstone_pcs']
					gemstone_detail.quantity = g['gemstone_weight']
					gemstone_detail.per_pcs_per_carat = g['per_pcs_per_carat']
					gemstone_detail.total_gemstone_rate = g['total_gemstone_rate']
					
				bom_doc.save()
				frappe.msgprint(("New BOM Created: {0}".format(get_link_to_form("BOM",bom_doc.name))))

	# @frappe.whitelist()
	# def get_details():
	# 	tag_numbers_by_stylebio = {}
		
	# 	for d in frappe.db.get_list("Old Stylebio Master",filters={"m_wo_ch_with_dia__mm_size_and_gem_with_brackets":1},fields=["old_stylebio","old_tag_no"]):
	# 		stylebio = d["old_stylebio"]
	# 		tag_no = d["old_tag_no"]
	# 		if stylebio not in tag_numbers_by_stylebio:
	# 			tag_numbers_by_stylebio[stylebio] = [tag_no]
	# 		else:
	# 			tag_numbers_by_stylebio[stylebio].append(tag_no)
		
	# 	for i in list(tag_numbers_by_stylebio.keys())[10:100]:
	# 		if i in frappe.db.get_list('Old BOM', pluck='name'):
	# 			continue
	# 		try:
	# 			session = requests.Session()
	# 			response = session.get(f"http://3.6.177.5:5000/api/stylebio/{i}")
				
	# 			if response.status_code == 200:
	# 				json_data = response.json()['data']
	# 				old_style_bio = i

	# 				old_bom_doc = frappe.new_doc("Old BOM")
	# 				old_bom_doc.old_stylebio = old_style_bio

	# 				# metal_detalis
	# 				 for m in json_data.keys():
	# 					if m in tag_numbers_by_stylebio[i]:
	# 						if json_data[m]['metal_data']:
	# 							metal_dict = old_bom_doc.append("old_bom_metal_details", {})
	# 							metal_dict.tag_no = m
	# 							metal_dict.old_stylebio = old_style_bio
	# 							metal_dict.metal_type = 'Gold'
	# 							metal_dict.metal_touch = metal_touch_dict[json_data[m]['metal_data']['Metal_Ratio']]
	# 							# frappe.throw(str(json_data[m]['metal_data']['Metal_Ratio']))
	# 							metal_dict.metal_purity = str(float(json_data[m]['metal_data']['Metal_Ratio']))
	# 							metal_dict.metal_colour = metal_colour_dict[json_data[m]['metal_data']['Metal_Color']]
	# 							metal_dict.metal_weight = json_data[m]['metal_data']['G_Weight']

	# 						if json_data[m]['diamond_data']:
	# 							diamond_dict = old_bom_doc.append("old_bom_diamond_details", {})
	# 							diamond_dict.tag_no = m
	# 							diamond_dict.old_stylebio = old_style_bio
	# 							diamond_dict.diamond_shape = str(json_data[m]['diamond_data']['Shape_Name']).capitalize()
	# 							diamond_dict.diamond_sieve_size = json_data[m]['diamond_data']['Type']
	# 							diamond_dict.diamond_pcs = json_data[m]['diamond_data']['Pcs']
	# 							diamond_dict.diamond_weight = json_data[m]['diamond_data']['Dia_Wt']
							
	# 						if json_data[m]['gemstone_data']:
	# 								for gt in json_data[m]['gemstone_data']['ERP_Name'].split(','):
	# 									gemstone_dict = old_bom_doc.append("old_bom_gemstone_details", {})
	# 									gemstone_dict.tag_no = m
	# 									gemstone_dict.old_stylebio = old_style_bio
										
	# 									gemstone_dict.gemstone_type = gt.lstrip().title()
	# 									if len(json_data[m]['gemstone_data']['ERP_Name'].split(',')) == 1:
	# 										gemstone_dict.cut_or_cab = json_data[m]['gemstone_data']['Cut_or_Cab'].lower().replace("cut","Faceted").replace("cab","Cabochon")
	# 									else:
	# 										gemstone_dict.cut_or_cab = cut_or_cab_dict[gt.lstrip().title()].lower().replace("cut","Faceted").replace("cab","Cabochon")
	# 									gemstone_dict.gemstone_shape = json_data[m]['gemstone_data']['Shape']

	# 									gemstone_dict.gemstone_quality = json_data[m]['gemstone_data']['Quality'].replace("Semi Precious","Semi-Precious")
	# 									gemstone_dict.gemstone_grade = json_data[m]['gemstone_data']['Grade']
	# 									gemstone_dict.total_gemstone_rate = json_data[m]['gemstone_data']['Amount']

	# 									gemstone_dict.gemstone_size = (json_data[m]['gemstone_data']['Size_Name'].replace(" X ","*") + " MM").replace("MM MM","MM")
	# 									gemstone_dict.gemstone_pcs = json_data[m]['gemstone_data']['Pcs']
	# 									gemstone_dict.gemstone_weight = json_data[m]['gemstone_data']['Weight']
	# 									gemstone_dict.per_pcs_per_carat = json_data[m]['gemstone_data']['UOM'].replace('Per Piece','Per Pc').replace('Per Pcarat','Per Pc')
	# 									if gemstone_dict.per_pcs_per_carat == '':
	# 										gemstone_dict.per_pcs_per_carat = "see design tag/cad"

	# 				old_bom_doc.insert()
	# 				frappe.msgprint(f"Creted {old_bom_doc.name}")
	# 		except:
	# 			frappe.db.set_value("Old Stylebio Master",{"old_stylebio":i},"error",1)
	# 			continue
	# 			# diamond_details
	# 			# for i in json_data.keys():
	# 			# 	if json_data[i]['diamond_data']:
	# 			# 		diamond_dict = old_bom_doc.append("old_bom_diamond_details", {})
	# 			# 		diamond_dict.tag_no = i
	# 			# 		diamond_dict.stylebio = old_style_bio
	# 			# 		diamond_dict.diamond_shape = str(json_data[i]['diamond_data']['Shape_Name']).capitalize()
	# 			# 		diamond_dict.diamond_sieve_size = json_data[i]['diamond_data']['Type']
	# 			# 		diamond_dict.diamond_pcs = json_data[i]['diamond_data']['Pcs']
	# 			# 		diamond_dict.diamond_weight = json_data[i]['diamond_data']['Dia_Wt']

	# 			# # # gemstone_details
	# 			# for i in json_data.keys():
	# 			# 		if json_data[i]['gemstone_data']:
	# 			# 			for gt in json_data[i]['gemstone_data']['ERP_Name'].split(','):
	# 			# 				gemstone_dict = old_bom_doc.append("old_bom_gemstone_details", {})
	# 			# 				gemstone_dict.tag_no = i
	# 			# 				gemstone_dict.stylebio = old_style_bio
								
	# 			# 				gemstone_dict.gemstone_type = gt.lstrip().title()
	# 			# 				if len(json_data[i]['gemstone_data']['ERP_Name'].split(',')) == 1:
	# 			# 					gemstone_dict.cut_or_cab = json_data[i]['gemstone_data']['Cut_or_Cab'].lower().replace("cut","Faceted").replace("cab","Cabochon")
	# 			# 				else:
	# 			# 					gemstone_dict.cut_or_cab = cut_or_cab_dict[gt.lstrip().title()].lower().replace("cut","Faceted").replace("cab","Cabochon")


	# 			# 				gemstone_dict.gemstone_shape = json_data[i]['gemstone_data']['Shape']

	# 			# 				gemstone_dict.gemstone_quality = json_data[i]['gemstone_data']['Quality'].replace("Semi Precious","Semi-Precious")
	# 			# 				gemstone_dict.gemstone_grade = json_data[i]['gemstone_data']['Grade']
	# 			# 				gemstone_dict.total_gemstone_rate = json_data[i]['gemstone_data']['Amount']

	# 			# 				gemstone_dict.gemstone_size = json_data[i]['gemstone_data']['Size_Name'].replace(" X ","*") + " MM"
	# 			# 				gemstone_dict.gemstone_pcs = json_data[i]['gemstone_data']['Pcs']
	# 			# 				gemstone_dict.gemstone_weight = json_data[i]['gemstone_data']['Weight']
	# 			# 				gemstone_dict.per_pcs_per_carat = json_data[i]['gemstone_data']['UOM'].replace('Per Piece','Per Pc').replace('Per Pcarat','Per Pc')
						
				
	# 			# frappe.db.set_value("Old Stylebio Master",{"old_stylebio":old_bom_doc.name},"created",1)
	# 			# frappe.msgprint(old_bom_doc.name)

	
	# @frappe.whitelist()
	# def get_details(old_stylebio):
		
	# 	session = requests.Session()
	# 	response = session.get(f"http://3.6.177.5:5000/api/stylebio/{old_stylebio}")

	# 	if response.status_code == 200:
	# 		json_data = response.json()['data']
	# 		old_style_bio = old_stylebio

	# 		metal_data = []
	# 		diamond_data = []
	# 		gemstone_data = []
	# 		for m in json_data.keys():
	# 			if json_data[m]['metal_data']:
	# 				metal_dict = {}
	# 				metal_dict['tagno'] = m
	# 				metal_dict['stylebio'] = old_style_bio
	# 				metal_dict['metal_type'] = 'Gold'
	# 				metal_dict['metal_touch'] = metal_touch_dict[json_data[m]['metal_data']['Metal_Ratio']]
	# 				metal_dict['metal_purity'] = float(json_data[m]['metal_data']['Metal_Ratio'])
	# 				try:
	# 					metal_dict['metal_colour'] = metal_colour_dict[json_data[m]['metal_data']['Metal_Color']]
	# 				except:
	# 					metal_dict['metal_colour'] = "see design tag/cad"
	# 				metal_dict['metal_weight'] = json_data[m]['metal_data']['G_Weight']
	# 				metal_data.append(metal_dict)

	# 			if json_data[m]['diamond_data']:
	# 				diamond_dict = {}
	# 				diamond_dict['tagno'] = m
	# 				diamond_dict['stylebio'] = old_style_bio
	# 				diamond_dict['diamond_shape'] = str(json_data[m]['diamond_data']['Shape_Name']).capitalize()
	# 				diamond_dict['diamond_sieve_size'] = json_data[m]['diamond_data']['Type']
	# 				diamond_dict['diamond_pcs'] = json_data[m]['diamond_data']['Pcs']
	# 				diamond_dict['diamond_weight'] = json_data[m]['diamond_data']['Dia_Wt']
	# 				diamond_data.append(diamond_dict)

	# 			if json_data[m]['gemstone_data']:
	# 				for gt in json_data[m]['gemstone_data']['ERP_Name'].split(','):
	# 					gemstone_dict = {}
	# 					gemstone_dict['tagno'] = m
	# 					gemstone_dict['stylebio'] = old_style_bio
						
	# 					gemstone_dict['gemstone_type'] = gt.lstrip().title()
	# 					if len(json_data[m]['gemstone_data']['ERP_Name'].split(',')) == 1:
	# 						gemstone_dict['cut_or_cab'] = json_data[m]['gemstone_data']['Cut_or_Cab'].lower().replace("cut","Faceted").replace("cab","Cabochon")
	# 					else:
	# 						gemstone_dict['cut_or_cab'] = cut_or_cab_dict[gt.lstrip().title()].lower().replace("cut","Faceted").replace("cab","Cabochon")
	# 					gemstone_dict['gemstone_shape'] = json_data[m]['gemstone_data']['Shape']

	# 					gemstone_dict['gemstone_quality'] = json_data[m]['gemstone_data']['Quality'].replace("Semi Precious","Semi-Precious")
	# 					gemstone_dict['gemstone_grade'] = json_data[m]['gemstone_data']['Grade']
	# 					gemstone_dict['total_gemstone_rate'] = json_data[m]['gemstone_data']['Amount']

	# 					gemstone_dict['gemstone_size'] = (json_data[m]['gemstone_data']['Size_Name'].replace(" X ","*") + " MM").replace("MM MM","MM")
	# 					gemstone_dict['gemstone_pcs'] = json_data[m]['gemstone_data']['Pcs']
	# 					gemstone_dict['gemstone_weight'] = json_data[m]['gemstone_data']['Weight']
	# 					gemstone_dict['per_pcs_per_carat'] = json_data[m]['gemstone_data']['UOM'].replace('Per Piece','Per Pc').replace('Per Pcarat','Per Pc')
	# 					if gemstone_dict['per_pcs_per_carat'] == '':
	# 						gemstone_dict['per_pcs_per_carat'] = "see design tag/cad"
	# 					gemstone_data.append(gemstone_dict)

	# 		return metal_data,diamond_data,gemstone_data
		

