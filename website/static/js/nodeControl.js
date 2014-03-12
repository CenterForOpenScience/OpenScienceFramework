/**
 * Controls the actions in the project header (make public/private, watch button,
 * forking, etc.)
 */

this.NodeControl = (function(ko, $, global) {
    'use strict';

    // Modal language
    var MESSAGES = {
        makePublicWarning: 'Once a project is made public, there is no way to guarantee that ' +
                            'access to the data it contains can be complete prevented. Users ' +
                            'should assume that once a project is made public, it will always ' +
                            'be public. Are you absolutely sure you would like to continue?',

        makePrivateWarning: 'Making a project private will prevent users from viewing it on this site, ' +
                            'but will have no impact on external sites, including Google\'s cache. ' +
                            'Would you like to continue?'
    };

    var URLS = {
        makePublic: global.nodeApiUrl + 'permissions/public/',
        makePrivate: global.nodeApiUrl + 'permissions/private/'
    };
    var PUBLIC = 'public';
    var PRIVATE = 'private';

    function beforeForkNode(url, done) {
        $.ajax({
            url: url,
            contentType: 'application/json'
        }).success(function(response) {
            bootbox.confirm(
                 $.osf.joinPrompts(response.prompts, 'Are you sure you want to fork this project?'),
                 function(result) {
                     if (result) {
                         done && done();
                     }
                 }
             )
        });
    }




    function setPermissions(permissions) {
        var msgKey = permissions === PUBLIC ? 'makePublicWarning' : 'makePrivateWarning';
        var urlKey = permissions === PUBLIC ? 'makePublic' : 'makePrivate';
        bootbox.confirm({
            title: "Warning",
            message: MESSAGES[msgKey],
            callback: function(result) {
                if (result) {
                    $.osf.postJSON(URLS[urlKey], {permissions: permissions},
                        function(data){
                            window.location.href = data.redirect_url;
                        }
                    );
                }
            }
        });
    }

    var removeUser = function(userid, name) {
        var payload = {
            id: userid,
            name: name
        };
        $.osf.postJSON(
            nodeApiUrl + 'beforeremovecontributors/',
            payload,
            function(response) {
                var prompt = $.osf.joinPrompts(response.prompts, 'Remove <strong>' + name + '</strong> from contributor list?');
                bootbox.confirm({
                    title: 'Delete Contributor?',
                    message: prompt,
                    callback: function(result) {
                        if (result) {
                            $.osf.postJSON(
                                nodeApiUrl + 'removecontributors/',
                                payload,
                                function(response) {
                                    if (response.redirectUrl) {
                                        window.location.href = response.redirectUrl;
                                    } else {
                                        window.location.reload();
                                    }
                                }
                            ).fail(function(xhr) {
                                var response = JSON.parse(xhr.responseText);
                                bootbox.alert('Error: ' + response.message_long);
                            });
                        }
                    }
                });
            }
        );
        return false;
    };

    /**
     * The ProjectViewModel, scoped to the project header.
     * @param {Object} data The parsed project data returned from the project's API url.
     */
    var ProjectViewModel = function(data) {
        var self = this;
        self._id = data.node.id;
        self.apiUrl = data.node.api_url;
        self.dateCreated = new FormattableDate(data.node.date_created);
        self.dateModified = new FormattableDate(data.node.date_modified);
        self.dateForked = new FormattableDate(data.node.forked_date);
        self.watchedCount = ko.observable(data.node.watched_count);
        self.userIsWatching = ko.observable(data.user.is_watching);
        self.userCanEdit = data.user.can_edit;
        self.description = data.node.description;
        self.title = data.node.title;
        self.category = data.node.category;
        self.isRegistration = data.node.is_registration;
        self.user = data.user;
        // The button text to display (e.g. "Watch" if not watching)
        self.watchButtonDisplay = ko.computed(function() {
            return self.watchedCount().toString();
        });
        self.watchButtonAction = ko.computed(function() {
            return self.userIsWatching() ? "Unwatch" : "Watch"
        })

        // Editable Title and Description
        if (self.userCanEdit) {
            var editableOptions = {
                type:  'text',
                pk:    self._id,
                url:   self.apiUrl + 'edit/',
                ajaxOptions: {
                    'type': 'POST',
                    "dataType": "json",
                    "contentType": "application/json"
                },
                params: function(params){
                    // Send JSON data
                    return JSON.stringify(params);
                },
                success: function(data){
                    document.location.reload(true);
                },
                placement: 'bottom'
            };

            // TODO: Remove hardcoded selectors.
            $('#nodeTitleEditable').editable($.extend({}, editableOptions, {
                name:  'title',
                title: 'Edit Title'
            }));
            $('#nodeDescriptionEditable').editable($.extend({}, editableOptions, {
                name:  'description',
                title: 'Edit Description',
                emptytext: "No description",
                emptyclass: "text-muted"
            }));
        }

        /**
         * Toggle the watch status for this project.
         */
        self.toggleWatch = function() {
            // Send POST request to node's watch API url and update the watch count
            $.ajax({
                url: self.apiUrl + "togglewatch/",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({}),
                contentType: "application/json",
                success: function(data, status, xhr) {
                    // Update watch count in DOM
                    self.userIsWatching(data['watched']);
                    self.watchedCount(data['watchCount']);
                }
            });
        };

        self.forkNode = function() {
            beforeForkNode(nodeApiUrl + 'fork/before/', function() {
                // Block page
                $.osf.block();
                // Fork node
                $.ajax({
                    url: nodeApiUrl + 'fork/',
                    type: 'POST'
                }).success(function(response) {
                    window.location = response;
                }).error(function() {
                    $.osf.unblock();
                    bootbox.alert('Forking failed');
                });
            });
        };

        self.makePublic = function() {
            return setPermissions(PUBLIC);
        };

        self.makePrivate = function() {
            return setPermissions(PRIVATE);
        };
    };

    ////////////////
    // Public API //
    ////////////////

    var defaults = {
        removeCss: '.user-quickedit'
    };


    function NodeControl (selector, data, options) {
        var self = this;
        self.selector = selector;
        self.$element = $(self.selector);
        self.data = data;
        self.viewModel = new ProjectViewModel(self.data);
        self.options = $.extend({}, defaults, options);
        self.init();
    }

    NodeControl.prototype.init = function() {
        var self = this;
        ko.applyBindings(self.viewModel, self.$element[0]);
        self._initRemoveLinks();
    };

    NodeControl.prototype._initRemoveLinks = function () {
        var self = this;
        $('.btn-remove').on('click', function() {
            var $this = $(this);
            removeUser($this.attr('data-userid'), $this.attr('data-fullname'));
        });
//        self.$removeElem = $('<span class="btn-remove-contrib"><i class="icon-remove"></i></span>');
//        $(self.options.removeCss).hover(
//            function(){
//                var me = $(this);
//                self.$removeElem.click(function(){
//                    // TODO: remove hardcoded attributes
//                    removeUser(me.attr('data-userid'), me.attr('data-fullname'));
//                    return false;
//                });
//                $(this).append(self.$removeElem);
//            },
//            function(){
//                self.$removeElem.remove();
//            }
//        );
    };

    return NodeControl;

})(ko, jQuery, window);
