from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

TRIGGERS = [
    ('advance', 'On order confirmation'),
    ('delivery', 'On full delivery'),
    ('commissioning', 'On project commissioned'),
]


class SolarMilestoneTemplate(models.Model):
    _name = 'solar.milestone.template'
    _description = 'Milestone Billing Template'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    line_ids = fields.One2many('solar.milestone.template.line', 'template_id', copy=True)
    total_percent = fields.Float(compute='_compute_total')

    @api.depends('line_ids.percent')
    def _compute_total(self):
        for t in self:
            t.total_percent = sum(t.line_ids.mapped('percent'))

    @api.constrains('line_ids')
    def _check_total(self):
        for t in self:
            if t.line_ids and float_compare(sum(t.line_ids.mapped('percent')), 100.0, precision_digits=2):
                raise ValidationError(_('Milestone percentages must add up to exactly 100 %.'))


class SolarMilestoneTemplateLine(models.Model):
    _name = 'solar.milestone.template.line'
    _description = 'Milestone Billing Template Line'
    _order = 'sequence, id'

    template_id = fields.Many2one('solar.milestone.template', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    percent = fields.Float(required=True)
    trigger_code = fields.Selection(TRIGGERS, required=True, default='advance')

    _sql_constraints = [('percent_positive', 'CHECK(percent > 0)', 'Percentage must be positive.')]