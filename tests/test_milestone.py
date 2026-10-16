from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMilestone(TransactionCase):

    def test_template_must_total_100(self):
        with self.assertRaises(ValidationError):
            self.env['solar.milestone.template'].create({
                'name': 'bad',
                'line_ids': [(0, 0, {'name': 'a', 'percent': 60, 'trigger_code': 'advance'}),
                             (0, 0, {'name': 'b', 'percent': 30, 'trigger_code': 'delivery'})]})

    def test_confirm_creates_project_and_advance_invoice(self):
        tmpl = self.env.ref('project_milestone_billing.template_30_50_20')
        partner = self.env['res.partner'].create({'name': 'MS customer'})
        product = self.env['product.product'].create({'name': 'Svc', 'type': 'service', 'list_price': 1000})
        order = self.env['sale.order'].create({
            'partner_id': partner.id, 'solar_milestone_template_id': tmpl.id,
            'order_line': [(0, 0, {'product_id': product.id, 'product_uom_qty': 1})]})
        order.action_confirm()
        self.assertTrue(order.solar_project_id)
        self.assertEqual(len(order.solar_milestone_ids), 3)
        adv = order.solar_milestone_ids.filtered(lambda m: m.trigger_code == 'advance')
        self.assertEqual(adv.state, 'invoiced')
        self.assertAlmostEqual(adv.invoice_id.amount_untaxed, 300.0, places=2)