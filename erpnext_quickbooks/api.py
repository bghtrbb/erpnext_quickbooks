# -*- coding: utf-8 -*-
# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from .exceptions import QuickbooksError
from .utils import disable_quickbooks_sync_on_exception, make_quickbooks_log
from pyqb.quickbooks import QuickBooks
from .sync_customers import *
from .sync_suppliers import *
from .sync_products import *
from .sync_employee import *
from .sync_orders import *
from .sync_purchase_invoice import *
from .sync_journal_vouchers import *
from .sync_entries import *
from .sync_account import *


@frappe.whitelist()
def sync_quickbooks():
	"Enqueue longjob for Syncing quickbooks Online"

	from frappe.utils.background_jobs import enqueue
	enqueue("erpnext_quickbooks.api.sync_quickbooks_resources", queue='long', timeout=1500, event="hourly_long")


@frappe.whitelist()
def sync_quickbooks_resources():
	quickbooks_settings = frappe.get_doc("Quickbooks Settings")

	make_quickbooks_log(title="Sync Job Queued", status="Queued", method=frappe.local.form_dict.cmd, message= "Sync Job Queued")
	
	if quickbooks_settings.enable_quickbooks_online:
		try :
			if quickbooks_settings.quickbooks_to_erpnext:
				validate_quickbooks_settings(quickbooks_settings)
				sync_from_quickbooks_to_erp(quickbooks_settings)
				make_quickbooks_log(title="Sync Completed", status="Success", method=frappe.local.form_dict.cmd, 
				message= "Updated {customers} customer(s)")

		except Exception, e:
			if e.args[0]:
				make_quickbooks_log(
					title="QuickBooks has suspended your account",
					status="Error",
					method="sync_quickbooks_resources",
					message=_("""QuickBooks has suspended your account till you complete the payment. We have disabled ERPNext Quickbooks Sync. Please enable it once your complete the payment at Quickbooks Online."""),
					exception=True)
					
				disable_quickbooks_sync_on_exception()
			
			else:
				make_quickbooks_log(
					title="sync has terminated",
					status="Error",
					method="sync_quickbooks_resources",
					message=frappe.get_traceback(),
					exception=True)
					
	else :
		make_quickbooks_log(title="Quickbooks connector is disabled",status="Error",method="sync_quickbooks_resources",
			message=_("""Quickbooks connector is not enabled. Click on 'Connect to Quickbooks' to connect ERPNext and your Quickbooks Online."""),
			exception=True)


def sync_from_quickbooks_to_erp(quickbooks_settings):

	quickbooks_obj = QuickBooks(
	    sandbox=True,
		client_id=quickbooks_settings.client_id,
		client_secret=quickbooks_settings.client_secret,
	    access_token=quickbooks_settings.access_token,
		access_token_key=quickbooks_settings.access_token_key,
	    company_id=quickbooks_settings.realm_id
	)
	sync_customers(quickbooks_obj)
	sync_suppliers(quickbooks_obj)
	create_Employee(quickbooks_obj)
	create_Item(quickbooks_obj)
	sync_Account(quickbooks_obj)
	sync_si_orders(quickbooks_obj)
	sync_pi_orders(quickbooks_obj)

	payment_invoice(quickbooks_obj)
	bill_payment(quickbooks_obj)
	sync_entry(quickbooks_obj)
	frappe.db.set_value("Quickbooks Settings", None, "last_sync_datetime", frappe.utils.now())

def validate_quickbooks_settings(quickbooks_settings):
	"""
		This will validate mandatory fields and access token or app credentials 
		by calling validate() of Quickbooks settings.
	"""
	try:
		quickbooks_settings.save()
	except QuickbooksError:
		disable_quickbooks_sync_on_exception()



def sync_from_erp_to_quickbooks():
	sync_erp_customers()
	sync_erp_suppliers()
	sync_erp_employees()
	sync_erp_accounts()
	sync_erp_items()
	sync_erp_purchase_invoices()
	sync_erp_purchase_invoices()
