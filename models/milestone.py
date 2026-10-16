import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .milestone_template import TRIGGERS

_logger = logging.getLogger(__name__)


class SolarMilestone(models.Model):
    _name = 'solar.milestone'
    _description = 'Billing Milestone'
    _inherit = ['mail.thread']
    _order = 'order_id, sequence, id'

    order_id = fields.Many2one('sale.order', required=True, ondelete='cascade', index=True)
    project_id = fields.Many2one(related='order_id.solar_project_id', store=True)
    currency_id = fields.Many2one(related='order_id.currency_id')
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    percent = fields.Float(required=True)
    trigger_code = fields.Selection(TRIGGERS, required=True)
    amount = fields.Monetary(compute='_compute_amount')
    state = fields.Selection([('pending', 'Pending'), ('invoiced', 'Invoiced')],
                             default='pending', tracking=True)
    invoice_id = fields.Many2one('account.move', readonly=True, copy=False)
    is_final = fields.Boolean(compute='_compute_is_final')

    @api.depends('order_id.amount_total', 'percent')
    def _compute_amount(self):
        for m in self:
            m.amount = m.order_id.amount_total * m.percent / 100.0

    @api.depends('order_id.solar_milestone_ids.sequence')
    def _compute_is_final(self):
        for m in self:
            siblings = m.order_id.solar_milestone_ids
            m.is_final = bool(siblings) and m == siblings.sorted(lambda x: (x.sequence, x.id))[-1]

    def unlink(self):
        if any(m.state == 'invoiced' for m in self):
            raise UserError(_('An invoiced milestone cannot be deleted.'))
        return super().unlink()

    def action_invoice(self):
        """Create the invoice for this milestone with Odoo's native down-payment wizard so
        accounting (down payment lines, deduction on final invoice) stays correct."""
        Wizard = self.env['sale.advance.payment.inv']
        for m in self:
            if m.state != 'pending':
                continue
            order = m.order_id
            if order.state != 'sale':
                raise UserError(_('Order %s must be confirmed before milestone invoicing.', order.name))
            order.invalidate_recordset(['invoice_ids'])
            before = order.invoice_ids
            ctx = {'active_model': 'sale.order', 'active_ids': order.ids, 'active_id': order.id}
            vals = {'advance_payment_method': 'delivered'} if m.is_final else {
                'advance_payment_method': 'percentage', 'amount': m.percent}
            Wizard.with_context(**ctx).create(vals).create_invoices()
            order.invalidate_recordset(['invoice_ids'])
            new = (order.invoice_ids - before)[:1]
            if not new:
                raise UserError(_('No invoice was generated for milestone %s.', m.name))
            m.write({'state': 'invoiced', 'invoice_id': new.id})
            m.message_post(body=_('Invoice %s created for milestone "%s" (%s%%).', new.display_name, m.name, m.percent))
            order.message_post(body=_('Milestone "%s" invoiced: %s', m.name, new.display_name))
        return True