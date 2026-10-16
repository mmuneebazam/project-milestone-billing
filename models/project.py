from odoo import api, fields, models


class ProjectProjectStage(models.Model):
    _inherit = 'project.project.stage'

    solar_milestone_code = fields.Selection([
        ('commissioning', 'Triggers commissioning milestone')], string='Billing Trigger')


class ProjectProject(models.Model):
    _inherit = 'project.project'

    solar_order_id = fields.Many2one('sale.order', string='Solar Sales Order', copy=False, readonly=True)
    solar_budget_cost = fields.Monetary(
        string='Budget Cost', currency_field='currency_id',
        groups='solar_security.group_solar_finance,solar_security.group_solar_manager')
    solar_planned_margin = fields.Monetary(
        string='Planned Margin', currency_field='currency_id', compute='_compute_planned_margin',
        groups='solar_security.group_solar_finance,solar_security.group_solar_manager')

    @api.depends('solar_order_id.amount_untaxed', 'solar_budget_cost')
    def _compute_planned_margin(self):
        for p in self:
            p.solar_planned_margin = p.solar_order_id.amount_untaxed - p.solar_budget_cost

    def write(self, vals):
        res = super().write(vals)
        if 'stage_id' in vals:
            for p in self:
                code = p.stage_id.solar_milestone_code
                if code and p.solar_order_id:
                    p.solar_order_id._solar_trigger_milestone(code)
        return res