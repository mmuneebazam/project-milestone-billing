from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        res = super()._action_done()
        for picking in self.filtered(lambda p: p.picking_type_code == 'outgoing' and p.state == 'done' and p.sale_id):
            order = picking.sale_id
            outs = order.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')
            if all(p.state in ('done', 'cancel') for p in outs):
                order._solar_trigger_milestone('delivery')
        return res