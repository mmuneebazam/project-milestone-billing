import logging

from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

PROJECT_TASKS = [
    # (name, requires installation sign-off)
    ('Site survey review', False),
    ('Permits & net metering', False),
    ('Procurement & delivery', False),
    ('Installation', True),
    ('Commissioning & handover', False),
]


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    solar_milestone_template_id = fields.Many2one('solar.milestone.template', string='Milestone Plan', copy=False)
    solar_milestone_ids = fields.One2many('solar.milestone', 'order_id', copy=False)
    solar_project_id = fields.Many2one('project.project', string='Solar Project', copy=False, readonly=True)

    def action_confirm(self):
        res = super().action_confirm()
        for order in self.filtered('solar_milestone_template_id'):
            if not order.solar_milestone_ids:
                order._solar_generate_milestones()
            if not order.solar_project_id:
                order._solar_create_project()
            order._solar_trigger_milestone('advance')
        return res

    def action_solar_regenerate_milestones(self):
        for order in self:
            if any(m.state == 'invoiced' for m in order.solar_milestone_ids):
                raise UserError(_('Some milestones are already invoiced; cannot regenerate.'))
            order.solar_milestone_ids.unlink()
            order._solar_generate_milestones()

    def _solar_generate_milestones(self):
        self.ensure_one()
        tmpl = self.solar_milestone_template_id
        self.env['solar.milestone'].create([{
            'order_id': self.id, 'sequence': l.sequence, 'name': l.name,
            'percent': l.percent, 'trigger_code': l.trigger_code,
        } for l in tmpl.line_ids])

    def _solar_get_analytic_account(self, project):
        if 'analytic_account_id' not in project._fields:
            return self.env['account.analytic.account']
        if project.analytic_account_id:
            return project.analytic_account_id
        plan = self.env['account.analytic.plan'].search([('parent_id', '=', False)], limit=1)
        if not plan:
            plan = self.env['account.analytic.plan'].create({'name': 'Projects'})
        acc = self.env['account.analytic.account'].create({
            'name': project.name, 'plan_id': plan.id, 'company_id': self.company_id.id,
            'partner_id': self.partner_id.id})
        project.analytic_account_id = acc
        return acc

    def _solar_create_project(self):
        self.ensure_one()
        project = self.env['project.project'].create({
            'name': '%s - %s' % (self.name, self.partner_id.name),
            'partner_id': self.partner_id.id,
            'user_id': self.user_id.id,
            'company_id': self.company_id.id,
            'solar_order_id': self.id,
            'solar_region_id': self.solar_region_id.id,
        })
        task_fields = self.env['project.task']._fields
        for seq, (name, signoff) in enumerate(PROJECT_TASKS, start=1):
            vals = {'name': name, 'project_id': project.id, 'sequence': seq, 'partner_id': self.partner_id.id}
            if signoff and 'solar_requires_signoff' in task_fields:
                vals['solar_requires_signoff'] = True
            self.env['project.task'].create(vals)
        acc = self._solar_get_analytic_account(project)
        if acc:
            self.order_line.filtered(lambda l: not l.display_type).write(
                {'analytic_distribution': {str(acc.id): 100}})
        self.solar_project_id = project
        return project

    def _solar_trigger_milestone(self, code):
        """Auto-invoice milestones. A failure never blocks the user's action (stock validation,
        stage change); it is posted on the order so finance can act."""
        for order in self:
            for m in order.solar_milestone_ids.filtered(lambda x: x.trigger_code == code and x.state == 'pending'):
                try:
                    with self.env.cr.savepoint():
                        m.action_invoice()
                except Exception as e:  # noqa
                    _logger.exception('Milestone invoice failed for %s', order.name)
                    order.message_post(body=_('Automatic invoicing of milestone "%s" failed: %s', m.name, e))