{
    'name': 'Project Milestone Billing',
    'version': '17.0.1.0.0',
    'summary': 'Milestone invoices (e.g. 30/50/20) driven by order confirmation, delivery and project stage',
    'category': 'Solar',
    'depends': ['solar_security', 'sale_management', 'sale_stock', 'project', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/milestone_data.xml',
        'views/milestone_views.xml',
        'views/sale_order_views.xml',
        'views/project_views.xml',
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
}