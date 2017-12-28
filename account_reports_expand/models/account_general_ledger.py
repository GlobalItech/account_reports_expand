from openerp import models, api, _
from openerp.tools.misc import formatLang
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import xlwt
from xlwt import Workbook, easyxf


import xlsxwriter
from odoo.exceptions import Warning
from datetime import timedelta, datetime
import babel
import calendar
import json
import StringIO
from odoo.tools import config, posix_to_ldml



class report_account_general_ledger(models.AbstractModel):
    _inherit = "account.general.ledger"
    #for formating to bring negative value 
    
    @api.model
    def _lines(self, line_id=None):
        
        lang_code = self.env.lang or 'en_US'
        lines = []
        context = self.env.context
        company_id = context.get('company_id') or self.env.user.company_id
        grouped_accounts = self.with_context(date_from_aml=context['date_from'], date_from=context['date_from'] and company_id.compute_fiscalyear_dates(datetime.strptime(context['date_from'], "%Y-%m-%d"))['date_from'] or None).group_by_account_id(line_id)  # Aml go back to the beginning of the user chosen range but the amount on the account line should go back to either the beginning of the fy or the beginning of times depending on the account
        sorted_accounts = sorted(grouped_accounts, key=lambda a: a.code)
        #unfold_all = context.get('print_mode') and not context['context_id']['unfolded_accounts']
        unfold_all = context.get('print_mode') and True or context.get('expand_all') and True
        for account in sorted_accounts:
            debit = grouped_accounts[account]['debit']
            credit = grouped_accounts[account]['credit']
            balance = grouped_accounts[account]['balance']
            amount_currency = '' if not account.currency_id else grouped_accounts[account]['amount_currency']
            lines.append({
                'id': account.id,
                'type': 'line',
                'name': account.code + " " + account.name,
                'footnotes': self.env.context['context_id']._get_footnotes('line', account.id),
                'columns': [amount_currency, self._format(debit), self._format(credit), self._format(balance)],
                'level': 2,
                'unfoldable': True,
                'unfolded': account in context['context_id']['unfolded_accounts'] or unfold_all,
                'colspan': 4,
            })
            if account in context['context_id']['unfolded_accounts'] or unfold_all:
                progress = 0
                domain_lines = []
                amls =amls_all = grouped_accounts[account]['lines']
                too_many = False
                if len(amls) > 80 and not context.get('print_mode'):
                    amls = amls[-80:]
                    too_many = True
                for line in amls:
                    if self.env.context['cash_basis']:
                        line_debit = line.debit_cash_basis
                        line_credit = line.credit_cash_basis
                    else:
                        line_debit = line.debit
                        line_credit = line.credit
                    progress = progress + line_debit - line_credit
                    currency = "" if not line.account_id.currency_id else line.amount_currency
                    name = []
                    name = line.name and line.name or ''
                    if line.ref:
                        name = name and name + ' - ' + line.ref or line.ref
                    if not context.get('print_mode') and len(name) > 35: 
                        name = name[:32] + "..."
                    else:    
                        if len(name) > 40 and not context.get('is_xlsx'):
                            tmp_name=name
                            new_name=''
                            while tmp_name:
                                new_name += tmp_name[:40] + "<br/>&nbsp;&nbsp;&nbsp;"
                                tmp_name = tmp_name[40:]
                            name = new_name
                        elif len(name) > 40 and context.get('is_xlsx'):
                            tmp_name=name
                            new_name=''
                            while tmp_name:
                                new_name += tmp_name[:40] + "\n"
                                tmp_name = tmp_name[40:]
                            name = new_name
                                
                    partner_name = line.partner_id.name
#                     if partner_name and len(partner_name) > 35:
#                         partner_name = partner_name[:32] + "..."
                    domain_lines.append({
                        'id': line.id,
                        'type': 'move_line_id',
                        'move_id': line.move_id.id,
                        'action': line.get_model_id_and_name(),
                        'name': line.move_id.name if line.move_id.name else '/',
                        'footnotes': self.env.context['context_id']._get_footnotes('move_line_id', line.id),
                        'columns': [line.date, name, partner_name, currency,
                                    line_debit != 0 and self._format(line_debit) or '',
                                    line_credit != 0 and self._format(line_credit) or '',
                                    self._format(progress)],
                        'level': 1,
                    })
                initial_debit = grouped_accounts[account]['initial_bal']['debit']
                initial_credit = grouped_accounts[account]['initial_bal']['credit']
                initial_balance = grouped_accounts[account]['initial_bal']['balance']
                initial_currency = '' if not account.currency_id else grouped_accounts[account]['initial_bal']['amount_currency']
                domain_lines[:0] = [{
                    'id': account.id,
                    'type': 'initial_balance',
                    'name': _('Initial Balance'),
                    'footnotes': self.env.context['context_id']._get_footnotes('initial_balance', account.id),
                    'columns': ['', '', '', initial_currency, self._format(initial_debit), self._format(initial_credit), self._format(initial_balance)],
                    'level': 1,
                }]
                domain_lines.append({
                    'id': account.id,
                    'type': 'o_account_reports_domain_total',
                    'name': _('Total ') + account.name,
                    'footnotes': self.env.context['context_id']._get_footnotes('o_account_reports_domain_total', account.id),
                    'columns': ['', '', '', amount_currency, self._format(debit), self._format(credit), self._format(balance)],
                    'level': 1,
                })
                if too_many:
                    domain_lines.append({
                        'id': account.id,
                         'domain': "[('id', 'in', %s)]" % amls_all.ids,
                        'type': 'too_many',
                        'name': _('There are more than 80 items in this list, click here to see all of them'),
                        'footnotes': [],
                        'colspan': 8,
                        'columns': [],
                        'level': 3,
                    })
                lines += domain_lines
        if len(context['context_id'].journal_ids) == 1 and context['context_id'].journal_ids.type in ['sale', 'purchase'] and not line_id:
            total = self._get_journal_total()
            lines.append({
                'id': 0,
                'type': 'total',
                'name': _('Total'),
                'footnotes': {},
                'columns': ['', '', '', '', self._format(total['debit']), self._format(total['credit']), self._format(total['balance'])],
                'level': 1,
                'unfoldable': False,
                'unfolded': False,
            })
            lines.append({
                'id': 0,
                'type': 'line',
                'name': _('Tax Declaration'),
                'footnotes': {},
                'columns': ['', '', '', '', '', '', ''],
                'level': 1,
                'unfoldable': False,
                'unfolded': False,
            })
            lines.append({
                'id': 0,
                'type': 'line',
                'name': _('Name'),
                'footnotes': {},
                'columns': ['', '', '', '', _('Base Amount'), _('Tax Amount'), ''],
                'level': 2,
                'unfoldable': False,
                'unfolded': False,
            })
            for tax, values in self._get_taxes().items():
                lines.append({
                    'id': tax.id,
                    'name': tax.name + ' (' + str(tax.amount) + ')',
                    'type': 'tax_id',
                    'footnotes': self.env.context['context_id']._get_footnotes('tax_id', tax.id),
                    'unfoldable': False,
                    'columns': ['', '', '', '', values['base_amount'], values['tax_amount'], ''],
                    'level': 1,
                })        
        return lines

    
    #this function overwrite the pdf function which is inhertred in account.context.general.ledger
class account_context_general_ledger(models.TransientModel):
    _inherit= "account.context.general.ledger"
   


    @api.multi
    def get_html_and_data(self, given_context=None):
        if given_context is None:
            given_context = {}
        result = {}
        if given_context:
            if 'force_account' in given_context and (not self.date_from or self.date_from == self.date_to):
                self.date_from = self.env.user.company_id.compute_fiscalyear_dates(datetime.strptime(self.date_to, "%Y-%m-%d"))['date_from']
                self.date_filter = 'custom'
        
        #expansion of button
        ctx = self._context.copy()
        if given_context.get('from_button'):
            ctx.update({'expand_all':given_context.get('expand_all')})
            self = self.with_context(ctx)

        lines = self.get_report_obj().get_lines(self)
        
        currency_id = self.env.user.company_id.currency_id
        currency = currency_id.symbol+' '+currency_id.name
        
        rcontext = {
            'res_company': self.env['res.users'].browse(self.env.uid).company_id,
            'context': self.with_context(**given_context), # context? rcontext with_context! Haaa... given_context!
            'report': self.get_report_obj(),
            'lines': lines,
            'footnotes': self.get_footnotes_from_lines(lines),
            'mode': 'display',
            'currency':currency,
        }
        result['html'] = self.env['ir.model.data'].xmlid_to_object(self.get_report_obj().get_template()).render(rcontext)
        result['report_type'] = self.get_report_obj().get_report_type().read(['date_range', 'comparison', 'cash_basis', 'analytic', 'extra_options'])[0]
        select = ['id', 'date_filter', 'date_filter_cmp', 'date_from', 'date_to', 'periods_number', 'date_from_cmp', 'date_to_cmp', 'cash_basis', 'all_entries', 'company_ids', 'multi_company', 'hierarchy_3', 'analytic']
        if self.get_report_obj().get_name() == 'general_ledger':
            select += ['journal_ids']
            result['available_journals'] = self.get_available_journal_ids_names_and_codes()
        if self.get_report_obj().get_name() == 'partner_ledger':
            select += ['account_type']
        result['report_context'] = self.read(select)[0]
        
        result['report_context'].update(self._context_add())
        if result['report_type']['analytic']:
            result['report_context']['analytic_account_ids'] = [(t.id, t.name) for t in self.analytic_account_ids]
            result['report_context']['analytic_tag_ids'] = [(t.id, t.name) for t in self.analytic_tag_ids]
            result['report_context']['available_analytic_account_ids'] = self.analytic_manager_id.get_available_analytic_account_ids_and_names()
            result['report_context']['available_analytic_tag_ids'] = self.analytic_manager_id.get_available_analytic_tag_ids_and_names()
        result['report_context'].update({'report_name':self._name}) #button loader for expand line with name which is getting report
        result['xml_export'] = self.env['account.financial.html.report.xml.export'].is_xml_export_available(self.get_report_obj())
        result['fy'] = {
            'fiscalyear_last_day': self.env.user.company_id.fiscalyear_last_day,
            'fiscalyear_last_month': self.env.user.company_id.fiscalyear_last_month,
        }
        result['available_companies'] = self.multicompany_manager_id.get_available_company_ids_and_names()
        return result
    
    def get_pdf(self):
        

        report_obj = self.get_report_obj()
        lines = report_obj.with_context(print_mode=True).get_lines(self)
        footnotes = self.get_footnotes_from_lines(lines)
        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'report_model':'account.general.ledger',
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.user.company_id,
        }
        
        current_time = datetime.now().strftime('%d/%m/%Y')
        current_time = 'Print Date : '+current_time
        currency_id = self.env.user.company_id.currency_id
        currency = currency_id.symbol+' '+currency_id.name

        body = self.env['ir.ui.view'].render_template(
            "account_reports.report_financial_letter",
            values=dict(rcontext, lines=lines, report=report_obj, currency=currency, context=self,current_time=current_time),
        )

        header = self.env['report'].render(
            "account_reports_ext.internal_layout_shahjad",
            values=rcontext,
        )
        header = self.env['report'].render(
            "report.minimal_layout",
            values=dict(rcontext, subst=True, body=header),
        )

        landscape = False
        if len(self.get_columns_names()) > 4:
            landscape = True

        return self.env['report']._run_wkhtmltopdf([header], [''], [(0, body)], landscape, self.env.user.company_id.paperformat_id, spec_paperformat_args={'data-report-margin-top': 10, 'data-report-header-spacing': 10})

    def get_full_date_names(self, dt_to, dt_from=None):
        convert_date = self.env['ir.qweb.field.date'].value_to_html
        date_to = convert_date(dt_to, None)
        dt_to = datetime.strptime(dt_to, "%Y-%m-%d")
        ctx = self._context.copy()
        if dt_from:
            date_from = convert_date(dt_from, None)
        else:
            date_from = convert_date(self.date_from, None)
            d = date_to
            date_to = date_from
            date_from = d
        if 'month' in self.date_filter:
            #return dt_to.strftime('%b %Y')
            if ctx.get('is_xls'):
                return '(From %s to  %s)' % (date_from, date_to)
            else:
                return '(From %s to  %s)' % (date_from, date_to)
        if 'quarter' in self.date_filter:
#             quarter = (dt_to.month - 1) / 3 + 1
            if ctx.get('is_xls'):
                return '(From %s to  %s)' % (date_from, date_to)
            else:
                return '(From %s to  %s)' % (date_from, date_to)
            #return dt_to.strftime('Quarter #' + str(quarter) + ' %Y')
        if 'year' in self.date_filter:
            if ctx.get('is_xls'):
                return '(From %s to  %s)' % (date_from, date_to)
            else:
                return '(From %s to  %s)' % (date_from, date_to)
#             lang = self.env.user.partner_id.lang
#             lang = self.env['res.lang'].search([('code','=',lang)])
#             if not lang:
#                 lang = self.env['res.lang'].search([])
#             date_format = lang.date_format     
#             if self.env.user.company_id.fiscalyear_last_day == 31 and self.env.user.company_id.fiscalyear_last_month == 12:
#                 return '(As of %s)' % (dt_to.strftime(date_format),)
#             else:
#                 d1 = dt_to - relativedelta(years=1)
#                 d1 = d1.strftime(date_format)
#                 return d1 + ' - ' + dt_to.strftime(date_format)
        if not dt_from:
            if ctx.get('is_xls'):
                return '(From %s to  %s)' % (date_from, date_to)
            else:
                return '(From %s to  %s)' % (date_from, date_to)
#             return '(As of %s)' % (date_to,)
        return '(From %s to  %s)' % (date_from, date_to)

    def get_columns_names(self):
        return [_("Date"), _("Communication"), _("Partner"), _("Currency"), _("Debit"), _("Credit"), _("Balance")]

    def get_xlsx(self, response):
        output = StringIO.StringIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        report_id = self.get_report_obj()
        sheet = workbook.add_worksheet(report_id.get_title())

        def_style = workbook.add_format({'font_name': 'Arial'})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        level_0_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
        level_0_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'left': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
        level_0_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
        level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2})
        level_1_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'left': 2})
        level_1_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2})
        level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2})
        level_2_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'left': 2})
        level_2_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'right': 2})
        level_3_style = def_style
        level_3_style_left = workbook.add_format({'font_name': 'Arial', 'left': 2})
        level_3_style_right = workbook.add_format({'font_name': 'Arial', 'right': 2})
        domain_style = workbook.add_format({'font_name': 'Arial', 'italic': True})
        domain_style_left = workbook.add_format({'font_name': 'Arial', 'italic': True, 'left': 2})
        domain_style_right = workbook.add_format({'font_name': 'Arial', 'italic': True, 'right': 2})
        upper_line_style = workbook.add_format({'font_name': 'Arial', 'top': 2})

        sheet.set_column(0, 0, 15) #  Set the first column width to 15

        sheet.write(0, 0, '', title_style)

        y_offset = 0
        if self.get_report_obj().get_name() == 'coa' and self.get_special_date_line_names():
            sheet.write(y_offset, 0, '', title_style)
            sheet.write(y_offset, 1, '', title_style)
            x = 2
            for column in self.with_context(is_xls=True).get_special_date_line_names():
                sheet.write(y_offset, x, column, title_style)
                sheet.write(y_offset, x+1, '', title_style)
                x += 2
            sheet.write(y_offset, x, '', title_style)
            y_offset += 1

        x = 1
        for column in self.with_context(is_xls=True).get_columns_names():
            sheet.write(y_offset, x, column.replace('<br/>', ' ').replace('&nbsp;',' '), title_style)
            x += 1
        y_offset += 1

        lines = report_id.with_context(no_format=True, print_mode=True).get_lines(self)

        if lines:
            max_width = max([len(l['columns']) for l in lines])

        for y in range(0, len(lines)):
            if lines[y].get('level') == 0 and lines[y].get('type') == 'line':
                for x in range(0, len(lines[y]['columns']) + 1):
                    sheet.write(y + y_offset, x, None, upper_line_style)
                y_offset += 1
                style_left = level_0_style_left
                style_right = level_0_style_right
                style = level_0_style
            elif lines[y].get('level') == 1 and lines[y].get('type') == 'line':
                for x in range(0, len(lines[y]['columns']) + 1):
                    sheet.write(y + y_offset, x, None, upper_line_style)
                y_offset += 1
                style_left = level_1_style_left
                style_right = level_1_style_right
                style = level_1_style
            elif lines[y].get('level') == 2:
                style_left = level_2_style_left
                style_right = level_2_style_right
                style = level_2_style
            elif lines[y].get('level') == 3:
                style_left = level_3_style_left
                style_right = level_3_style_right
                style = level_3_style
            elif lines[y].get('type') != 'line':
                style_left = domain_style_left
                style_right = domain_style_right
                style = domain_style
            else:
                style = def_style
                style_left = def_style
                style_right = def_style
            sheet.write(y + y_offset, 0, lines[y]['name'], style_left)
            for x in xrange(1, max_width - len(lines[y]['columns']) + 1):
                sheet.write(y + y_offset, x, None, style)
            for x in xrange(1, len(lines[y]['columns']) + 1):
                if isinstance(lines[y]['columns'][x - 1], tuple):
                    lines[y]['columns'][x - 1] = lines[y]['columns'][x - 1][0]
                if x < len(lines[y]['columns']):
                    sheet.write(y + y_offset, x+lines[y].get('colspan', 1)-1, lines[y]['columns'][x - 1], style)
                else:
                    sheet.write(y + y_offset, x+lines[y].get('colspan', 1)-1, lines[y]['columns'][x - 1], style_right)
            if lines[y]['type'] == 'total' or lines[y].get('level') == 0:
                for x in xrange(0, len(lines[0]['columns']) + 1):
                    sheet.write(y + 1 + y_offset, x, None, upper_line_style)
                y_offset += 1
        if lines:
            for x in xrange(0, max_width+1):
                sheet.write(len(lines) + y_offset, x, None, upper_line_style)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
