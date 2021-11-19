# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2021 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name": "Sale Order Sync",
    "version": "14.0.1.2.0",
    "author": "Vertel",
    "category": "Sales",
    "description": """
14.0.1.2.0 - Added sync of res.partners.
14.0.1.0.1 - Added a call to check_order_stock
Synchronizes sale orders from Odoo 14 to Odoo 8
using triggers.
""",
    "depends": ["sale", "base_automation"],
    "external_dependencies": {
        "python": ["odoorpc"],
    },
    "data": [
        "views/sale_order_sync.xml",
    ],
    "installable": True,
    "application": False,
}
