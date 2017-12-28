odoo.define('account_reports_ext.account_report_general_ledger_generic', function (require) {
'use strict';

var core = require('web.core');
var Model = require('web.Model');
var Pager = require('web.Pager');
var session = require('web.session');
var account_report_generic = require('account_reports.account_report_generic');
var Dialog = require('web.Dialog');
var QWeb = core.qweb;
var framework = require('web.framework');
var crash_manager = require('web.crash_manager');

account_report_generic.include({
	render_buttons: function() {
        var self = this;
        this.$buttons = $(QWeb.render("accountReports.buttons", {xml_export: this.xml_export,report_name: this.report_context.report_name,context : this.report_context}));

        // pdf output
        this.$buttons.siblings('.o_account-widget-pdf').bind('click', function () {
            framework.blockUI();
            session.get_file({
                url: self.controller_url.replace('output_format', 'pdf'),
                complete: framework.unblockUI,
                error: crash_manager.rpc_error.bind(crash_manager),
            });
        });

        // xls output
        this.$buttons.siblings('.o_account-widget-xlsx').bind('click', function () {
            framework.blockUI();
            session.get_file({
                url: self.controller_url.replace('output_format', 'xlsx'),
                complete: framework.unblockUI,
                error: crash_manager.rpc_error.bind(crash_manager),
            });
        });

        // xml output
        this.$buttons.siblings('.o_account-widget-xml').bind('click', function () {
            // For xml exports, first check if the export can be done
            return new Model('account.financial.html.report.xml.export').call('check', [self.report_model, self.report_id]).then(function (check) {
                if (check === true) {
                    framework.blockUI();
                    session.get_file({
                        url: self.controller_url.replace('output_format', 'xml'),
                        complete: framework.unblockUI,
                        error: crash_manager.rpc_error.bind(crash_manager),
                    });
                } else { // If it can't be done, show why.
                    Dialog.alert(this, check, {});
                }
            });
        });
        this.$buttons.siblings('.o_account-widget-expand').bind('click', function () {
        	//session.user_context.expand_all = true;
        	var expand = false;
        	if (self.given_context.expand_all) {
        		expand=false;
        	}
        	else
        	{
        		expand=true;
        	}
        	self.do_action({
        		type: 'ir.actions.client',
        		tag: 'account_report_generic',
        		context: {'url': '/account_reports/output_format/general_ledger/1', 'model': 'account.general.ledger','context':{'from_button':true,'expand_all':expand}},
        		});
        	});
        return this.$buttons;
    },
    
	/*render_buttons: function() {
        var self = this;
        var buttons = this._super();
        
        // xml output
        this.$buttons.siblings('.o_account-widget-expand').bind('click', function () {
        	session.user_context.expand_all = true;
        	self.do_action({
        		type: 'ir.actions.client',
        		tag: 'account_report_generic',
        		context: {'url': '/account_reports/output_format/general_ledger/1', 'model': 'account.general.ledger'},
        		});
        	});
        return buttons
	}*/
});

});