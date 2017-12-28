{
    'name': 'Add Expand button General Ledger report',
    'category': 'Account',
    'author': 'itech Resources',
    'sequence': 100,
    'summary': 'Reporting Format',
    'website': 'http://itechresources.net/',
    'version': '1.0',
    'description': """
    This module will has added Expand button for expanding uniformly all records in the General Ledger. 
            """,
    'depends': ["account_reports"],
    #'depends': ["account_reports_old_module"],
    'data': [
        'views/report_financial.xml',
    ],   
    'qweb': [
            'static/src/xml/account_report_backend.xml',
            ],  
    'installable': True,
    'application': False,
	'price':20.00,
    'currency':'EUR', 
}
