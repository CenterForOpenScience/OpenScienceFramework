'use strict';
require('css/registrations.css');

var ko = require('knockout');
var $ = require('jquery');

var $osf = require('js/osfHelpers');
var RegistrationManager = require('js/registrationUtils').RegistrationManager;

var ctx = window.contextVars;
var node = window.contextVars.node;

$(document).ready(function() {

    $('#registrationsTabs').tab();
    $('#registrationsTabs a').click(function (e) {
        e.preventDefault();
        $(this).tab('show');
    });

    var draftManager = new RegistrationManager(node, '#draftRegistrationScope', {
        list: node.urls.api + 'draft/',
        // TODO: uncomment when we support draft submission for review
        //submit: node.urls.api + 'draft/{draft_pk}/submit/',
        delete: node.urls.api + 'draft/{draft_pk}/',
        schemas: '/api/v1/project/schema/',
        edit: node.urls.web + 'draft/{draft_pk}/'
    });
    draftManager.init();

    $('#registerNode').click(function(event) {
        event.preventDefault();
        draftManager.beforeCreateDraft();        
    });
});
