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


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _connect_to_host(self):
        try:
            host = self.env["ir.config_parameter"].sudo().get_param("rpc_host")
            port = self.env["ir.config_parameter"].sudo().get_param("rpc_port")
            db = self.env["ir.config_parameter"].sudo().get_param("rpc_db")
            user = self.env["ir.config_parameter"].sudo().get_param("rpc_user")
            password = self.env["ir.config_parameter"].sudo().get_param("rpc_password")
            conn = odoorpc.ODOO(host=host, port=port)
            conn.login(db, login=user, password=password)
            return conn

        except Exception as e:
            _logger.warning(f"Could not connect to host. {e}")

    def sync_sale_order(self):
        """Connects to a remote odoo server and syncronizes the sale order"""
        _logger.info("Syncronizing sale.order...")

        odoo_conn = self._connect_to_host()

        if odoo_conn and self.state in ["sale", "sent"]:
            model = self.env["ir.model.data"]
            pricelist_name = model.search(
                [
                    ("res_id", "=", self.pricelist_id.id),
                    ("model", "=", "product.pricelist"),
                ]
            ).name
            partner_name = model.search(
                [("res_id", "=", self.partner_id.id), ("model", "=", "res.partner")]
            ).name
            partner_shipping_name = model.search(
                [
                    ("res_id", "=", self.partner_invoice_id.id),
                    ("model", "=", "res.partner"),
                ]
            ).name
            partner_invoice_name = model.search(
                [
                    ("res_id", "=", self.partner_shipping_id.id),
                    ("model", "=", "res.partner"),
                ]
            ).name

            try:
                try:
                    target_pricelist_id = int(pricelist_name.split("_")[-1])
                except ValueError:
                    target_pricelist_id = 3
                target_partner_id = int(partner_name.split("_")[-1])
                target_partner_shipping_id = (
                    int(partner_shipping_name.split("_")[-1])
                    if partner_invoice_name
                    else False
                )
                target_partner_invoice_id = (
                    int(partner_invoice_name.split("_")[-1])
                    if partner_invoice_name
                    else False
                )
            except Exception as e:
                _logger.exception(e)
                return False

            try:
                sale_order_vals = {
                    "partner_id": target_partner_id,
                    "partner_invoice_id": target_partner_invoice_id,
                    "partner_shipping_id": target_partner_shipping_id,
                    "name": self.name,
                    "amount_untaxed": self.amount_untaxed,
                    "amount_tax": self.amount_tax,
                    "amount_total": self.amount_total,
                    "date_order": str(self.date_order),
                    "pricelist_id": target_pricelist_id,
                    "carrier_id": 32,  # Hardcoded for now
                    "payment_term": 18,  # Hardcoded for now 'Förskott'
                    "picking_policy": "one",
                }
                sale_order_id = odoo_conn.env["sale.order"].create(sale_order_vals)
                line_ids = []

                for line in self.order_line:
                    product_id = odoo_conn.env["product.product"].search(
                        [("default_code", "=", line.product_id.default_code)]
                    )

                    if not product_id:
                        _logger.exception(
                            f"Product does not exist in other DB {line.product_id.default_code} {line.product_id.name}"
                        )
                        raise

                    line_vals = {
                        "name": line.name,
                        "order_id": sale_order_id,
                        "order_partner_id": target_partner_id,
                        "price_unit": line.price_unit,
                        "price_subtotal_incl": line.price_subtotal,
                        "product_id": product_id[0],
                        "product_uom_qty": line.product_uom_qty,
                    }
                    sale_order_line_id = odoo_conn.env["sale.order.line"].create(
                        line_vals
                    )
                    line_ids.append(sale_order_line_id)

                sale_order = odoo_conn.env["sale.order"].browse(sale_order_id)
                sale_order.write({"order_line": [(6, 0, line_ids)]})
                # Confirm the sale order in target
                sale_order.action_button_confirm()
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
