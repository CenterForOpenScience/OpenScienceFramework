'use strict';
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var Raven = require('raven-js');
var ko = require('knockout');
require('js/qToggle');
require('js/onboarder.js');
require('js/components/autocomplete');

$(function(){
    $('.prereg-button').qToggle();
    $('.prereg-button').click(function(){
        var target = $(this).attr('data-qToggle-target');
        var input = $(target).find('input').first().focus();
    });

    $('#newProject').click( function() {
        var title = $('#newProjectTitle').val();
        $osf.postJSON('/api/v1/project/new/', { title: title }).done(function(response) {
            window.location = response.projectUrl + 'registrations/';
        }).fail(function() {
            $osf.growl('Project creation failed. Reload the page and try again.');
        });
    });

    // Activate "existing projects" typeahead.
    $.getJSON('/api/v1/dashboard/get_nodes/').done(function(response) {
        var allNodes = response.nodes;

        // If we need to change what nodes can be registered, filter here
        var registrationSelection = ko.utils.arrayFilter(allNodes, function(node) {
            return $.inArray(node.permissions, ['admin']) !== -1;
        });

        $osf.applyBindings({
            nodes: registrationSelection,
            enableComponents: true
        }, '#existingProject');
    }).fail(function(xhr, textStatus, error) {
        Raven.captureMessage('Could not fetch dashboard nodes.', {
            url: '/api/v1/dashboard/get_nodes/', textStatus: textStatus, error: error
        });
    });

    // Activate autocomplete for draft registrations
    $.getJSON('/api/v1/prereg/draft_registrations/').done(function(response){
        if (response.draftRegistrations.length) {
            $osf.applyBindings({}, '#existingPrereg');
        }
    });
});
