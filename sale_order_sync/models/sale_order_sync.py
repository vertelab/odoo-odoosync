from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)
try:
    import odoorpc
except ImportError:
    raise Warning(
        "odoorpc library missing. Please install the library. Eg: pip3 install odoorpc"
    )

PREFIX = "__ma_import__"


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _connect_to_host(self):
        try:
            host = self.env["ir.config_parameter"].sudo().get_param("rpc_host")
            port = self.env["ir.config_parameter"].sudo().get_param("rpc_port")
            db = self.env["ir.config_parameter"].sudo().get_param("rpc_db")
            user = self.env["ir.config_parameter"].sudo().get_param("rpc_user")
            password = self.env["ir.config_parameter"].sudo(
            ).get_param("rpc_password")
            conn = odoorpc.ODOO(host=host, port=port)
            conn.login(db, login=user, password=password)
            return conn

        except Exception as e:
            _logger.warning(f"Could not connect to host. {e}")

    def create_external_id(self, model, partner_id, remote_id):
        """Expected external ID(odoo14) of remote model record(odoo8)."""
        ext_id_vals = {
            "module": PREFIX,  # __ma_import__
            "model": "res.partner",  # Modelnamn på Odoo 14
            "res_id": partner_id,  # ID på Odoo 14
            # Sträng med modelnamn i Odoo 14 och ID på Odoo 8 på formen: res_partner_41820
            "name": model.replace(".", '_') + "_" + str(remote_id),
        }

        self.env["ir.model.data"].create(ext_id_vals)
        return PREFIX + "." + model.replace(".", '_') + "_" + str(remote_id)

    def signup(self, values, token=None):
        """Connects to a remote odoo8 server and syncronize/create account"""
        _logger.info("Syncronizing res.users...")

        odoo8_conn = self._connect_to_host()
        
        if odoo8_conn:
            db, login, password = super().signup(values=values, token=token)
            partner = self.env['res.users'].search([
                ("login", "=", login),
            ]).partner_id
            model = self.env["ir.model.data"]
            # Create a new partner in target Odoo.
            target_country = odoo8_conn.env["res.country"].search(
                [("code", "=", partner.country_id.code)], limit=1
            )
            partner_name = model.search(
                [("res_id", "=", partner.id),
                 ("model", "=", "res.partner")]
            ).name

            target_partner_vals = {
                "name": partner.name,
                "type": partner.type,
                "mobile": partner.phone,
                "email": partner.email,
                "street": partner.street,
                "street2": partner.street2,
                "zip": partner.zip,
                "city": partner.city,
                "country_id": target_country[0] if target_country else False,
                "category_id": [(4, 233, 0)],  # slutkonsument
                "lang": partner.lang,
            }
            _logger.warning(f"PARTNER NAME: {partner_name} LOFDAN EKSVIC")
            if partner_name:
                partner_name = partner_name.split('_')[-1]
                target_partner = False

                target_partner = odoo8_conn.env['res.partner'].browse(
                    int(partner_name)
                )

                _logger.warning("UPDATING A PARTNER: DANLOF: EKSVIC")

                target_partner.write(target_partner_vals)

                _logger.warning("UPDATING A PARTNER: DANLOF: EKSVIC 2")
                if target_partner:
                    _logger.warning("UPDATING A PARTNER: DANLOF: EKSVIC 3")
                    #_logger.warning(f"partner is : {partner.read()}")
                    # sync adresses for the customer
                    # if partner.child_ids:
                    #     for adress in partner.child_ids.filtered(
                    #         lambda r: r.type in ["delivery", "invoice"]
                    #     ):
                    #         _logger.warning("UPDATING A PARTNER: DANLOF: EKSVIC 4")
                    #         target_adress_vals = {
                    #             "name": adress.name,
                    #             "type": adress.type,
                    #             "mobile": adress.phone,
                    #             "email": adress.email,
                    #             "street": adress.street,
                    #             "street2": adress.street2,
                    #             "zip": adress.zip,
                    #             "city": adress.city,
                    #             "country_id": target_country[0]
                    #             if target_country
                    #             else False,
                    #             "category_id": [(4, 233, 0)],  # slutkonsument
                    #             "lang": adress.lang,
                    #         }
                    #         domain = model.search([
                    #                 ('module', '=', PREFIX),
                    #                 ('res_id', '=', adress.id),
                    #                 ('model', '=', 'res.partner')
                    #         ])
                    #         types = [self.env['res.partner'].browse(item.res_id).type for item in domain]
                    #         _logger.warning(f"Types: {types} DANLOF: EKSVIC")
                    #         if adress.type in types:
                    #             _logger.warning("UPDATING A PARTNER ADRESS: DANLOF: EKSVIC")
                    #             for child in target_partner.child_ids:
                    #                 if child.type == adress.type:
                    #                     child.write(target_adress_vals)
                    #         else:
                    #             _logger.warning("CREATING A PARTNER ADRESS: DANLOF: EKSVIC")
                    #             target_adress_vals.update({
                    #                 "parent_id": target_partner.id,
                    #             })
                    #             _logger.warning(f"TARGET VALS: ===== {target_adress_vals}")
                    #             adress_id = odoo8_conn.env['res.partner'].create(
                    #                 target_adress_vals
                    #             )
                    #             _logger.warning(f"EXTERNALLY CREATED ID IS: {f'res_partner_{adress_id}'}")
                    #             model.create(
                    #                 {
                    #                     "module": PREFIX,
                    #                     "name": f"res_partner_{adress_id}",
                    #                     "model": "res.partner",
                    #                     "res_id": adress.id,
                    #                 }
                    #             )
            else:
                # ANONYMOUS CHECKOUT PARTNER CREATION START
                _logger.warning("SOMETHING ELSE HAPPENS HERE")
                target_partner_id = odoo8_conn.env["res.partner"].create(
                    target_partner_vals
                )

                if target_partner_id:
                    self.create_external_id(
                        'res.partner', partner.id, target_partner_id)
                else:
                    _logger.warning(f'Target Partner ID IS FALSE, VERY BAD!')

                # sync adresses for the customer
                for adress in partner.child_ids.filtered(
                    lambda r: r.type in ["delivery", "invoice"]
                ):
                    target_adress_vals = {
                        "parent_id": target_partner_id,
                        "name": adress.name,
                        "type": adress.type,
                        "mobile": adress.phone,
                        "email": adress.email,
                        "street": adress.street,
                        "street2": adress.street2,
                        "zip": adress.zip,
                        "city": adress.city,
                        "country_id": target_country[0]
                        if target_country
                        else False,
                        "category_id": [(4, 233, 0)],  # slutkonsument
                        "lang": adress.lang,
                    }
                    odoo8_conn.env["res.partner"].create(target_adress_vals)
                    # ANONYMOUS CHECKOUT PARTER CREATION END
            _logger.warning(db, login, password)
            return (db, login, password)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _connect_to_host(self):
        try:
            host = self.env["ir.config_parameter"].sudo().get_param("rpc_host")
            port = self.env["ir.config_parameter"].sudo().get_param("rpc_port")
            db = self.env["ir.config_parameter"].sudo().get_param("rpc_db")
            user = self.env["ir.config_parameter"].sudo().get_param("rpc_user")
            password = self.env["ir.config_parameter"].sudo(
            ).get_param("rpc_password")
            conn = odoorpc.ODOO(host=host, port=port)
            conn.login(db, login=user, password=password)
            return conn

        except Exception as e:
            _logger.warning(f"Could not connect to host. {e}")

    def sync_sale_order(self):
        """Connects to a remote odoo server and syncronizes the sale order"""
        _logger.info("Syncronizing sale.order...")

        odoo8_conn = self._connect_to_host()

        target_country = odoo8_conn.env["res.country"].search(
            [("code", "=", self.partner_id.country_id.code)], limit=1
        )

        # ANONYMOUS CHECKOUT PARTER CREATION START
        target_partner_vals = {
            "name": self.partner_id.name,
            "type": self.partner_id.type,
            "mobile": self.partner_id.phone,
            "email": self.partner_id.email,
            "street": self.partner_id.street,
            "street2": self.partner_id.street2,
            "zip": self.partner_id.zip,
            "city": self.partner_id.city,
            "country_id": target_country[0] if target_country else False,
            "category_id": [(4, 233, 0)],  # slutkonsument
            "lang": self.partner_id.lang,
        }

        if odoo8_conn and self.state in ["sale", "sent"]:
            model = self.env["ir.model.data"]
            pricelist_name = model.search(
                [
                    ("res_id", "=", self.pricelist_id.id),
                    ("model", "=", "product.pricelist"),
                ]
            ).name
            partner_name = model.search(
                [("res_id", "=", self.partner_id.id),
                 ("model", "=", "res.partner")]
            ).name

            _logger.warning(f"SALE ORDER PARTERNAME: DANLOF: {partner_name}")

            if partner_name:
                partner_name = partner_name.split('_')[-1]

                target_partner = False

                target_partner = odoo8_conn.env['res.partner'].browse(
                    int(partner_name)
                )

                _logger.warning("UPDATING A PARTNER: DANLOF: EKSVIC")

                target_partner.write(target_partner_vals)

                if target_partner:
                    # sync adresses for the customer
                    for adress in self.partner_id.child_ids.filtered(
                        lambda r: r.type in ["delivery", "invoice"]
                    ):
                        target_adress_vals = {
                            "name": adress.name,
                            "type": adress.type,
                            "mobile": adress.phone,
                            "email": adress.email,
                            "street": adress.street,
                            "street2": adress.street2,
                            "zip": adress.zip,
                            "city": adress.city,
                            "country_id": target_country[0]
                            if target_country
                            else False,
                            "category_id": [(4, 233, 0)],  # slutkonsument
                            "lang": adress.lang,
                        }
                        domain = model.search([
                                ('module', '=', PREFIX),
                                ('res_id', '=', adress.id),
                                ('model', '=', 'res.partner')
                        ])
                        types = [self.env['res.partner'].browse(item.res_id).type for item in domain]
                        if adress.type in types:
                            _logger.warning("UPDATING A PARTNER ADRESS: DANLOF: EKSVIC")
                            for child in target_partner.child_ids:
                                if child.type == adress.type:
                                    child.write(target_adress_vals)
                        else:
                            _logger.warning("CREATING A PARTNER ADRESS: DANLOF: EKSVIC")
                            target_adress_vals.update({
                                "parent_id": target_partner.id,
                            })
                            _logger.warning(f"TARGET VALS: ===== {target_adress_vals}")
                            adress_id = odoo8_conn.env['res.partner'].create(
                                target_adress_vals
                            )
                            _logger.warning(f"ADDRESS ID IS: {f'res_partner_{adress_id}'}")
                            model.create(
                                {
                                    "module": PREFIX,
                                    "name": f"res_partner_{adress_id}",
                                    "model": "res.partner",
                                    "res_id": adress.id,
                                }
                            )
                    target_partner = target_partner.id;

            if not partner_name:
                # No external id found for res.partner in source Odoo
                # -> this res.partner did not come from target Odoo.
                # We need to see if it exists in target Odoo and if not, create it.

                # Removed this as it caused problems since odoo creates duplicate
                # res.partners when creating orders with the same email in the webshop.
                # try to find a matching partner in target.
                # target_partner_id = odoo_conn.env["res.partner"].search(
                #     [("email", "=", self.partner_id.email)], limit=1
                # )
                # Added this to force the if to always enter the else
                target_partner = False
                if target_partner:
                    target_partner = target_partner[0]
                else:
                    # Create a new partner in target Odoo.
                    target_country = odoo8_conn.env["res.country"].search(
                        [("code", "=", self.partner_id.country_id.code)], limit=1
                    )

                    # ANONYMOUS CHECKOUT PARTER CREATION START
                    target_partner = odoo8_conn.env["res.partner"].create(
                        target_partner_vals
                    )

                    # sync adresses for the customer
                    for adress in self.partner_id.child_ids.filtered(
                        lambda r: r.type in ["delivery", "invoice"]
                    ):
                        target_adress_vals = {
                            # "parent_id": target_partner_id,
                            "name": adress.name,
                            "type": adress.type,
                            "mobile": adress.phone,
                            "email": adress.email,
                            "street": adress.street,
                            "street2": adress.street2,
                            "zip": adress.zip,
                            "city": adress.city,
                            "country_id": target_country[0]
                            if target_country
                            else False,
                            "category_id": [(4, 233, 0)],  # slutkonsument
                            "lang": adress.lang,
                        }
                        created_adress = odoo8_conn.env["res.partner"].create(
                            target_adress_vals)
                        model.create(
                            {
                                "module": PREFIX,
                                "name": f"res_partner_{created_adress}",
                                "model": "res.partner",
                                "res_id": adress.id,
                            }
                        )
                    # ANONYMOUS CHECKOUT PARTER CREATION END

                # Create an external id in source Odoo so that we can find
                # it quicker next time.
                model.create(
                    {
                        "module": PREFIX,
                        "name": f"res_partner_{target_partner}",
                        "model": "res.partner",
                        "res_id": self.partner_id.id,
                    }
                )
            
            _logger.warning(f"invoice ID: {self.partner_invoice_id.id}")
            partner_shipping_name = model.search(
                [
                    ("res_id", "=", self.partner_shipping_id.id ),
                    ("model", "=", "res.partner"),
                ]
            ).name
            partner_invoice_name = model.search(
                [
                    ("res_id", "=", self.partner_invoice_id.id),
                    ("model", "=", "res.partner"),
                ]
            ).name

            sale_order_invoice_type = odoo8_conn.env.ref('__invoice_type.webshop_invoice_type')
            _logger.warning(f"DANLOF Invoice type: {sale_order_invoice_type}");
            
            if self.partner_id.agent_ids:
                agent_name = model.search(
                    [
                        ("res_id", "=", self.partner_id.agent_ids[0].id),
                        ("model", "=", "res.partner"),
                    ]
                ).name
                commission_name = model.search(
                    [
                        ("res_id", "=",
                         self.partner_id.agent_ids[0].commission_id.id),
                        ("model", "=", "sale.commission"),
                    ]
                ).name
            else:
                agent_name = False

            try:
                # Removed this code. The default pricelist form odoo 8
                # will be used now instead.
                # try:
                #     target_pricelist_id = int(pricelist_name.split("_")[-1])
                # except ValueError:
                #     target_pricelist_id = 3
                if not target_partner:
                    target_partner = int(partner_name.split("_")[-1])
                target_partner_shipping_id = (
                    int(partner_shipping_name.split("_")[-1])
                    if partner_shipping_name
                    else False
                )
                target_partner_invoice_id = (
                    int(partner_invoice_name.split("_")[-1])
                    if partner_invoice_name
                    else False
                )
                if agent_name:
                    target_agent_id = (
                        int(agent_name.split("_")[-1]) if agent_name else False
                    )
                    target_commission_id = (
                        int(commission_name.split("_")[-1])
                        if commission_name
                        else False
                    )
            except Exception as e:
                _logger.exception(e)
                return False

            try:
                _logger.warning(f'partner_invoice_id: {target_partner_invoice_id} \n partner_shipping_id: {target_partner_shipping_id}')

                #
                sale_order_vals = {
                    "partner_id": target_partner,
                    "partner_invoice_id": target_partner_invoice_id,
                    "partner_shipping_id": target_partner_shipping_id,
                    "name": self.name,
                    "amount_untaxed": self.amount_untaxed,
                    "amount_tax": self.amount_tax,
                    "amount_total": self.amount_total,
                    "date_order": str(self.date_order),
                    # "pricelist_id": target_pricelist_id,
                    "carrier_id": 32,  # Hardcoded for now
                    "invoice_type_id": 7, # Hardcoded for now
                    "picking_policy": "one",
                }

                _logger.warning(f"THIS IS SALEORDERVALS: {sale_order_vals}")
                sale_order_id = odoo8_conn.env["sale.order"].create(
                    sale_order_vals)
                line_ids = []

                for line in self.order_line:
                    product_id = False
                    if line.product_id.default_code:
                        product_id = odoo8_conn.env["product.product"].search(
                            [("default_code", "=", line.product_id.default_code)],
                            limit=1,
                        )
                        if not product_id:
                            product_name = model.search(
                                [
                                    ("res_id", "=", line.product_id.id),
                                    ("model", "=", "product.product"),
                                ]
                            ).name
                            product_id = odoo8_conn.env["product.product"].search(
                                [("id", "=", product_name.split("_")[-1])]
                            )
                    elif (
                        line.product_id.name[0:12] == "Free Product"
                        and line.product_id.type == "service"
                    ):
                        # This is a free product generated by odoo from a coupon
                        # we translate this to the "Discount" product in target Odoo
                        product_id = [
                            odoo8_conn.env.ref(
                                "__export__.product_product_4963").id
                        ]

                    if not product_id:
                        _logger.error(
                            f"Product does not exist in other DB {line.product_id.default_code} {line.product_id.name}"
                        )
                        raise Exception

                    line_vals = {
                        "name": line.name,
                        "order_id": sale_order_id,
                        "order_partner_id": target_partner,
                        "price_unit": line.price_unit,
                        "price_subtotal_incl": line.price_subtotal,
                        "product_id": product_id[0],
                        "product_uom_qty": line.product_uom_qty,
                    }
                    sale_order_line_id = odoo8_conn.env["sale.order.line"].create(
                        line_vals
                    )
                    line_ids.append(sale_order_line_id)

                sale_order = odoo8_conn.env["sale.order"].browse(sale_order_id)
                sale_order.write({"order_line": [(6, 0, line_ids)]})

                # create kickback data.
                if agent_name:
                    for so_line in sale_order.order_line:
                        agent_line_vals = {
                            "sale_line": so_line.id,
                            "agent": target_agent_id,
                            "commission": target_commission_id,
                        }
                        so_line.write({"agents": [(0, 0, agent_line_vals)]})
                # Removed this else since this is the default behaviour now.
                # else:
                #     _logger.warning(
                #         "Sale order without agents data! %s" % sale_order.name
                #     )
                # Confirm the sale order in target
                sale_order.check_order_stock()
                # Use this line if we want to send email.
                # Currently we do not want to.
                # sale_order.with_context(send_email=True).action_button_confirm()
                sale_order.action_button_confirm()
                for picking_id in sale_order.picking_ids:
                    picking_id.action_assign()
                    picking_id.write({'ready4picking': True})
                # change order to state done to indicate that it has been
                # transfered correctly
                self.state = "done"
                _logger.info("Order sent.")

            except Exception as e:
                # Orders that failed sync are left in state "sale".
                # TODO: add better handling
                _logger.exception(e)
        else:
            _logger.info("No connection or sale order")
