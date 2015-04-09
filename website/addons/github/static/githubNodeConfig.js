'use strict';

var ko = require('knockout');
require('knockout.punches');
var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');

var $osf = require('js/osfHelpers');

ko.punches.enableAll();

var noop = function() {};

var ViewModel = function(url, selector) {
    var self = this;

    self.accounts = ko.observable([]);

    self.url = url;
    self.selector = selector;

    self.nodeHasAuth = ko.observable(false);
    self.userHasAuth = ko.observable(false);
    self.userIsOwner = ko.observable(false);
    self.ownerName = ko.observable('');

    self.urls = ko.observable({});
    self.loadedSettings = ko.observable(false);
    self.repoList = ko.observableArray([]);
    self.loadedRepoList = ko.observable(false);
    self.currentRepo = ko.observable('');
    self.selectedRepo = ko.observable('');

    self.accessToken = ko.observable('');

    self.loading = ko.observable(false);
    self.creating = ko.observable(false);
    self.creatingCredentials = ko.observable(false);

    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');

    self.showSelect = ko.observable(false);

    self.showSettings = ko.pureComputed(function() {
        return self.nodeHasAuth();
    });
    self.disableSettings = ko.pureComputed(function() {
        return !(self.userHasAuth() && self.userIsOwner());
    });
    self.showNewRepo = ko.pureComputed(function() {
        return self.userHasAuth() && self.userIsOwner();
    });
    self.showImport = ko.pureComputed(function() {
        return self.userHasAuth() && !self.nodeHasAuth();
    });
    self.showCreateCredentials = ko.pureComputed(function() {
        return !self.nodeHasAuth() && !self.userHasAuth();
    });
    self.canChange = ko.pureComputed(function() {
        return self.userIsOwner() && self.nodeHasAuth();
    });
    self.allowSelectRepo = ko.pureComputed(function() {
        return (self.repoList().length > 0 || self.loadedRepoList()) && (!self.loading());
    });


};


ViewModel.prototype.toggleSelect = function() {
    var self = this;
    self.showSelect(!self.showSelect());
    return self.updateRepoList();
};

ViewModel.prototype.selectRepo = function() {
    var self = this;
    self.loading(true);
    debugger;
    return $osf.postJSON(
            self.urls().config, {
                'github_repo': self.selectedRepo()
            }
        )
        .done(function(response) {
            self.updateFromData(response);
            self.changeMessage('Successfully linked Github repo \'' + self.currentRepo() + '\'. Go to the <a href="' +
                               self.filesUrl + '">Files page</a> to view your content.', 'text-success');
            self.loading(false);
        })
        .fail(function(xhr, status, error) {
            self.loading(false);
            var message = 'Could not change Github repo at this time. ' +
                'Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
            self.changeMessage(message, 'text-warning');
            Raven.captureMessage('Could not set Github repo', {
                url: self.urls().setRepo,
                textStatus: status,
                error: error
            });
        });
};

ViewModel.prototype.connectAccount = function() {
    var self = this;

    window.oauthComplete = function(res) {
        // Update view model based on response
        self.changeMessage('Successfully imported Github credentials.', 'text-success', 3000);
        self.updateAccounts()
            .done(function() {
                $osf.putJSON(
                    self.urls().importAuth, {
                        external_account_id: self.accounts()[0].id
                    }
                ).then(self.onImportSuccess.bind(self), self.onImportError.bind(self));
            });
    };
    window.open(self.urls().auth);
};

ViewModel.prototype.connectExistingAccount = function(account_id) {
        var self = this;

        return $osf.putJSON(
            self.urls().importAuth, {
                external_account_id: account_id
            }
        ).done(function(response) {
            self.changeMessage('Successfully imported Github credentials.', 'text-success');
            self.updateFromData(response);

        }).fail(function(xhr, status, error) {
            var message = 'Could not import Github credentials at ' +
                'this time. Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
            self.changeMessage(message, 'text-warning');
            Raven.captureMessage('Could not import Github credentials', {
                url: self.urls().importAuth,
                textStatus: status,
                error: error
            });
        });
};


ViewModel.prototype._deauthorizeNodeConfirm = function() {
    var self = this;
    return $.ajax({
        type: 'DELETE',
        url: self.urls().deauthorize,
        contentType: 'application/json',
        dataType: 'json'
    }).done(function(response) {
        self.updateFromData(response);
    }).fail(function(xhr, status, error) {
        var message = 'Could not deauthorize Github at ' +
            'this time. Please refresh the page. If the problem persists, email ' +
            '<a href="mailto:support@osf.io">support@osf.io</a>.';
        self.changeMessage(message, 'text-warning');
        Raven.captureMessage('Could not remove Github authorization.', {
            url: self.urls().deauthorize,
            textStatus: status,
            error: error
        });
    });
};

ViewModel.prototype.deauthorizeNode = function() {
    var self = this;
    bootbox.confirm({
        title: 'Deauthorize Github?',
        message: 'Are you sure you want to remove this Github authorization?',
        callback: function(confirm) {
            if (confirm) {
                self._deauthorizeNodeConfirm();
            }
        }
    });
};




ViewModel.prototype.updateRepoList = function(){
    var self = this;
    return self.fetchRepoList()
        .done(function(repos){
            self.repoList(repos);
            self.selectedRepo(self.currentRepo());
        });
};


ViewModel.prototype.createRepo = function(repoName) {
    var self = this;
    self.creating(true);
    repoName = repoName.toLowerCase();
    return $osf.postJSON(
        self.urls().create_repo, {
            repo_name: repoName
        }
    ).done(function(response) {
        self.creating(false);
        self.repoList(response.repos);
        self.loadedRepoList(true);
        self.selectedRepo((self.ownerName() + " / "+ repoName));
        self.showSelect(true);
        var msg = 'Successfully created repo "' + repoName + '". You can now select it from the drop down list.';
        var msgType = 'text-success';
        self.changeMessage(msg, msgType);
    }).fail(function(xhr) {
        var resp = JSON.parse(xhr.responseText);
        var message = resp.message;
        var title = resp.title || 'Problem creating repo';
        self.creating(false);
        if (!message) {
            message = 'Looks like that name is taken. Try another name?';
        }
        bootbox.confirm({
            title: title,
            message: message,
            callback: function(result) {
                if (result) {
                    self.openCreateRepo();
                }
            }
        });
    });
};

ViewModel.prototype.openCreateRepo = function() {
    var self = this;

    var isValidRepo = /^(?!.*(\.\.|-\.))[^.][a-z0-9\d.-]{2,61}[^.]$/;

    bootbox.prompt('Name your new repo', function(repoName) {
        if (!repoName) {
            return;
        } else if (isValidRepo.exec(repoName) == null) {
            bootbox.confirm({
                title: 'Invalid repo name',
                message: 'Sorry, that\'s not a valid repo name. Try another name?',
                callback: function(result) {
                    if (result) {
                        self.openCreateRepo();
                    }
                }
            });
        } else {
            self.createRepo(repoName);
        }
    });
};

ViewModel.prototype.fetchRepoList = function() {
    var self = this;

    var ret = $.Deferred();
    if(self.loadedRepoList()){
        ret.resolve(self.repoList());
    }
    else{
         $.ajax({
            url: self.urls().repo_list,
            type: 'GET',
            dataType: 'json'
        }).done(function(response) {
            self.loadedRepoList(true);
            ret.resolve(response.repo_names);
        })
        .fail(function(xhr, status, error) {
            var message = 'Could not retrieve list of Github repos at' +
                'this time. Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
            self.changeMessage(message, 'text-warning');
            Raven.captureMessage('Could not GET github repo list', {
                url: self.urls().repo_list,
                textStatus: status,
                error: error
            });
            ret.reject(xhr, status, error);
        });
    }
    return ret.promise();
};


ViewModel.prototype.updateFromData = function(data) {
    var self = this;
    var ret = $.Deferred();
    var applySettings = function(settings){

        self.nodeHasAuth(settings.nodeHasAuth);
        self.userHasAuth(settings.userHasAuth);
        self.userIsOwner(settings.userIsOwner);
        self.ownerName(settings.ownerName);
        self.currentRepo(settings.repo);
        self.urls(settings.urls);
        debugger;
        ret.resolve(settings);
    };
    if (typeof data === 'undefined'){
        return self.fetchFromServer()
            .done(applySettings);
    }
    else {
        applySettings(data);
    }
    return ret.promise();
};


ViewModel.prototype.fetchFromServer = function() {
    var self = this;
    var ret = $.Deferred();
    $.ajax({
        url: self.url,
        type: 'GET',
        dataType: 'json',
        contentType: 'application/json'
    })
    .done(function(response) {
        var settings = response.result;
        self.loadedSettings(true);
        ret.resolve(settings);
    })
    .fail(function(xhr, status, error) {
        var message = 'Could not retrieve Github settings at ' +
                'this time. Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
        self.changeMessage(message, 'text-warning');
        Raven.captureMessage('Could not GET github settings', {
            url: self.url,
            textStatus: status,
            error: error
        });
        ret.reject(xhr, status, error);
    });
    return ret.promise();
};


/** Change the flashed message. */
ViewModel.prototype.changeMessage = function(text, css, timeout) {
    var self = this;
    self.message(text);
    var cssClass = css || 'text-info';
    self.messageClass(cssClass);
    if (timeout) {
        // Reset message after timeout period
        setTimeout(function() {
            self.message('');
            self.messageClass('text-info');
        }, timeout);
    }
};


ViewModel.prototype.fetchAccounts = function() {
    var self = this;
    var ret = $.Deferred();
    var request = $.get(self.urls().accounts);
    request.then(function(data) {
        ret.resolve(data.accounts);
    });
    request.fail(function(xhr, textStatus, error) {
        self.changeMessage('Could not retrieve GitHub  account list at ' +
                    'this time. Please refresh the page. If the problem persists, email ' +
                    '<a href="mailto:support@osf.io">support@osf.io</a>.', 'text-warning');
        Raven.captureMessage('Could not GET ' + self.addonName + ' accounts for user', {
            url: self.url,
            textStatus: textStatus,
            error: error
        });
        ret.reject(xhr, textStatus, error);
    });
    return ret.promise();
};

ViewModel.prototype.updateAccounts = function() {
    var self = this;
    return self.fetchAccounts()
        .done(function(accounts) {
            self.accounts(
                $.map(accounts, function(account) {
                    return {
                        name: account.display_name,
                        id: account.id
                    };
                })
            );
        });
};

ViewModel.prototype.importAuth = function() {
    var self = this;
    self.updateAccounts()
        .then(function(){
            if (self.accounts().length > 1) {
                bootbox.prompt({
                    title: 'Choose GitHub Access Token to Import',
                    inputType: 'select',
                    inputOptions: ko.utils.arrayMap(
                        self.accounts(),
                        function(item) {
                            return {
                                text: item.name,
                                value: item.id
                            };
                        }
                    ),
                    value: self.accounts()[0].id,
                    callback: (self.connectExistingAccount.bind(self))
                });
            } else {
                bootbox.confirm({
                    title: 'Import GitHub Access Token?',
                    message: 'Are you sure you want to authorize this project with your github access token?',
                    callback: function(confirmed) {
                        if (confirmed) {
                            self.connectExistingAccount.call(self, (self.accounts()[0].id));
                        }
                    }
                });
            }
        });
}





var githubConfig = function(selector, url){
    var viewModel = new ViewModel(url, selector);
    $osf.applyBindings(viewModel, selector);
    viewModel.updateFromData();
};

module.exports = {
    githubNodeConfig: githubConfig,
    _githubNodeConfigViewModel: ViewModel
};