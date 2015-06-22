/*
 * TODO, bring the register page up to date.
 *
 */
var $ = require('jquery');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');
var ctx = window.contextVars;


var preRegisterMessage =  function(title, parentTitle, parentUrl, category) {
    // TODO(hrybacki): Remove warning once Retraction/Embargoes goes is merged into production
    if (parentUrl) {
        return 'You are about to register the ' + category + ' <b>' + title +
            '</b> and everything that is inside it. This will <b>not</b> register' +
            ' its parent, <b>' + parentTitle + '</b>.' +
            ' If you want to register the parent, please go <a href="' +
            parentUrl + '">here.</a>' +
            '<hr /><b>Important Note:</b> As early as <u>June 8, 2015</u>, registrations ' +
            'will be made public immediately or can be embargoed for up to one year. ' +
            'There will no longer be the option of creating a permanently private ' +
            'registration. If you register before June 8, 2015 and leave your ' +
            'registration private, then the registration can remain private. After June 8, 2015, ' +
            'if you ever make it public, you will not be able to return it to private. ';
    } else {
        return 'You are about to register <b>' + title +
            '</b> and everything that is inside it. Registration creates a permanent, ' +
            'time-stamped, uneditable version of the project. If you would prefer to ' +
            'register a particular component, please navigate to that component and then ' +
            'initiate registration. '+
            // TODO(hrybacki): Remove once Retraction/Embargoes goes is merged into production
            '<hr /><b>Important Note:</b> As early as <u>June 8, 2015</u>, registrations ' +
            'will be made public immediately or can be embargoed for up to one year. ' +
            'There will no longer be the option of creating a permanently private ' +
            'registration. If you register before June 8, 2015 and leave your ' +
            'registration private, then the registration can remain private. After June 8, 2015, ' +
            'if you ever make it public, you will not be able to return it to private.';
    }
};

function draft_failed() {
    $osf.unblock();
    bootbox.alert('Draft failed');
}

function draftNode() {

    // Block UI until request completes
    $osf.block();

    // POST data
    $.ajax({
        url:  ctx.node.urls.api + 'draft/' + ctx.regTemplate + '/',
        type: 'POST',
        //contentType: 'application/json',
    }).done(function(response) {
        if (response.status === 'success') {
            window.location.href = response.result;
        }
        else if (response.status === 'error') {
            draft_failed();
        }
    }).fail(function() {
        draft_failed();
    });

    // Stop event propagation
    return false;

}

$(document).ready(function() {
    $('#registerNode').click(function(event) {
        var node = window.contextVars.node;
        var target = event.currentTarget.href;

        event.preventDefault();
        var title = node.title;
        var parentTitle = node.parentTitle;
        var parentRegisterUrl = node.parentRegisterUrl;
        var category = node.category;
        var bootboxTitle = 'Register Project';
        if (node.category !== 'project'){
            category = 'component';
            bootboxTitle = 'Register Component';
        }

        bootbox.confirm({
            title: bootboxTitle,
            message: preRegisterMessage(title, parentTitle, parentRegisterUrl, category),
            callback: function (confirmed) {
                if(confirmed) {
                    // this is where is would be set to a draft
                    //draftNode();
                    window.location.href = target;
                }
            }
        });
    });
});
