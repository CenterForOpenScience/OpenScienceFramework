'use strict';

var ko = require('knockout');
var Raven = require('raven-js');
var $osf = require('js/osfHelpers');
var $modal = $('#ownCloudCredentialsModal');
var oop = require('js/oop');
var osfHelpers = require('js/osfHelpers');
var OauthAddonFolderPicker = require('js/oauthAddonNodeConfig')._OauthAddonNodeConfigViewModel;
var language = require('js/osfLanguage').Addons.owncloud;

var ViewModel = oop.extend(OauthAddonFolderPicker,{
    constructor: function(addonName, url, selector, folderPicker, opts, tbOpts) {
        var self = this;
        self.super.constructor(addonName, url, selector, folderPicker, tbOpts);
        // Non-Oauth fields:
        self.username = ko.observable("");
        self.password = ko.observable("");
        self.hosts = ko.observableArray([]);
        self.selectedHost = ko.observable();    // Host specified in select element
        self.customHost = ko.observable();      // Host specified in input element
        self.savedHost = ko.observable();       // Configured host

        const otherString = 'Other (Please Specify)';
        // Designated host, specified from select or input element
        self.host = ko.pureComputed(function() {
            return self.useCustomHost() ? self.customHost() : self.selectedHost();
        });
        // Hosts visible in select element. Includes presets and "Other" option
        self.visibleHosts = ko.pureComputed(function() {
            return self.hosts().concat([otherString]);
        });
        // Whether to use select element or input element for host designation
        self.useCustomHost = ko.pureComputed(function() {
            return self.selectedHost() === otherString;
        });
        self.credentialsChanged = ko.pureComputed(function() {
            return self.nodeHasAuth() && !self.validCredentials();
        });
        self.showCredentialInput = ko.pureComputed(function() {
            return (self.credentialsChanged() && self.userIsOwner()) ||
                (!self.userHasAuth() && !self.nodeHasAuth() && self.loadedSettings());
        });
    },
    _updateCustomFields: function(settings) {
        var self = this;
        self.hosts(settings.hosts);
    },
    clearModal : function() {
        var self = this;
        self.selectedHost(null);
        self.customHost(null);
    },
    connectAccount : function() {
        var self = this;
        if( !self.selectedHost() ){
            self.setMessage("Please select a OwnCloud server.", 'text-danger');
            return;
        }
        if ( !self.useCustomHost() && !self.username() && !self.password() ){
            self.setMessage("Please enter a username and password.", 'text-danger');
            return;
        }
        if ( self.useCustomHost() && ( !self.customHost() || !self.username() || !self.password() ) )  {
            self.setMessage("Please enter a OwnCloud host and credentials.", 'text-danger');
            return;
        }
        var url = self.urls().auth;
        return osfHelpers.postJSON(
            url,
            ko.toJS({
                host: self.host,
                password: self.password,
                username: self.username
            })
        ).done(function() {
            self.clearModal();
            $modal.modal('hide');
            self.updateAccounts().then(function() {
                try{
                    $osf.putJSON(
                        self.urls().importAuth, {
                            external_account_id: self.accounts()[0].id
                        }
                    ).done(self.onImportSuccess.bind(self)
                    ).fail(self.onImportError.bind(self));
                    self.changeMessage(self.messages.connectAccountSuccess(), 'text-success', 3000);
                }
                catch(err){
                    self.changeMessage(self.messages.connectAccountDenied(), 'text-danger', 6000);
                }
            });
        }).fail(function(xhr, textStatus, error) {
            var errorMessage = (xhr.status === 401) ? language.authInvalid : language.authError;
            self.changeMessage(errorMessage, 'text-danger');
            Raven.captureMessage('Could not authenticate with OwnCloud', {
                url: url,
                textStatus: textStatus,
                error: error
            });
        });
    },
});

function OwnCloudNodeConfig(selector, url) {
    var self = this;
    self.viewModel = new ViewModel('owncloud', url, selector, '#owncloudGrid', {});
    self.viewModel.updateFromData();
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = OwnCloudNodeConfig;
